import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.config import settings
from app.models import (
    Application, ApplicationApproval, AuditEvent,
    Job, CandidateProfile, ApplicationStatus, User
)
from app.schemas import ApplicationOut
from app.services.verification_service import VerificationService
from app.integrations.browser import BrowserAutomationService

logger = logging.getLogger(__name__)

class ApplicationServiceError(Exception):
    pass

class DuplicateApplicationError(ApplicationServiceError):
    pass

class MissingApprovalError(ApplicationServiceError):
    pass

class IncompleteProfileError(ApplicationServiceError):
    pass

class ApplicationService:
    def __init__(self):
        self.verifier = VerificationService()
        self.browser_service = BrowserAutomationService()

    def record_approval(
        self,
        db: Session,
        user_id: str,
        job_id: str,
        answers: Dict[str, Any]
    ) -> ApplicationApproval:
        """
        Records explicit candidate consent for applying to a specific job and profile version.
        """
        # Validate profile exists
        profile = db.query(CandidateProfile).filter(CandidateProfile.user_id == user_id).first()
        if not profile:
            raise IncompleteProfileError("No candidate profile found. Please upload or create a profile first.")

        # Validate job exists
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise ApplicationServiceError(f"Job with ID '{job_id}' not found.")

        # Check existing application to prevent duplicate submissions
        existing_app = db.query(Application).filter(
            Application.user_id == user_id,
            Application.job_id == job_id
        ).first()

        if existing_app and existing_app.status in [
            ApplicationStatus.SUBMITTED.value,
            ApplicationStatus.VERIFIED.value,
            ApplicationStatus.SUBMITTING.value
        ]:
            raise DuplicateApplicationError(
                f"An application for this job has already been processed (Current status: {existing_app.status})."
            )

        # Record or update Approval
        approval = db.query(ApplicationApproval).filter(
            ApplicationApproval.user_id == user_id,
            ApplicationApproval.job_id == job_id
        ).first()

        if not approval:
            approval = ApplicationApproval(
                user_id=user_id,
                job_id=job_id,
                profile_version=profile.version,
                answers=answers,
                approved_at=datetime.now(timezone.utc)
            )
            db.add(approval)
        else:
            approval.profile_version = profile.version
            approval.answers = answers
            approval.approved_at = datetime.now(timezone.utc)

        # Create or update application state to APPROVED
        if not existing_app:
            existing_app = Application(
                user_id=user_id,
                job_id=job_id,
                status=ApplicationStatus.APPROVED.value,
                resume_version=profile.version,
                application_url=job.url
            )
            db.add(existing_app)
        else:
            existing_app.status = ApplicationStatus.APPROVED.value
            existing_app.resume_version = profile.version
            existing_app.application_url = job.url

        # Log audit event
        audit = AuditEvent(
            user_id=user_id,
            action="application_approved",
            resource_type="job",
            resource_id=job_id,
            details={
                "job_title": job.title,
                "company": job.company,
                "profile_version": profile.version
            }
        )
        db.add(audit)

        db.commit()
        db.refresh(approval)
        return approval

    def save_job(self, db: Session, user_id: str, job_id: str) -> Application:
        """
        Saves a job to candidate's tracked application list with SAVED status.
        """
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise ApplicationServiceError(f"Job with ID '{job_id}' not found.")

        existing_app = db.query(Application).filter(
            Application.user_id == user_id,
            Application.job_id == job_id
        ).first()

        if existing_app:
            return existing_app

        app = Application(
            user_id=user_id,
            job_id=job_id,
            status=ApplicationStatus.SAVED.value,
            application_url=job.url
        )
        db.add(app)
        db.commit()
        db.refresh(app)
        return app

    async def execute_submission(
        self,
        db: Session,
        user_id: str,
        application_id: str
    ) -> Application:
        """
        Executes an approved application workflow.
        Enforces user consent, checks live submission flag, validates fields, and records truth-in-status.
        Never fabricates submission receipts or claims an unconfirmed application was submitted.
        """
        app = db.query(Application).filter(
            Application.id == application_id,
            Application.user_id == user_id
        ).first()

        if not app:
            raise ApplicationServiceError("Application record not found.")

        # Require explicit approval
        approval = db.query(ApplicationApproval).filter(
            ApplicationApproval.user_id == user_id,
            ApplicationApproval.job_id == app.job_id
        ).first()

        if not approval:
            raise MissingApprovalError(
                "Explicit candidate approval is mandatory before any application can be submitted."
            )

        profile = db.query(CandidateProfile).filter(CandidateProfile.user_id == user_id).first()
        job = db.query(Job).filter(Job.id == app.job_id).first()

        if not profile or not profile.email:
            raise IncompleteProfileError("Candidate profile must contain at least an email address.")

        # Atomic transition to SUBMITTING
        app.status = ApplicationStatus.SUBMITTING.value
        db.commit()

        # Check safety guardrail
        if not settings.ENABLE_LIVE_SUBMISSIONS:
            # When live submissions are disabled for user safety:
            # Mark as READY_TO_APPLY with official guidance, do NOT claim successful submission
            app.status = ApplicationStatus.READY_TO_APPLY.value
            app.submission_reference = None
            app.submitted_at = None
            app.verification_details = {
                "mode": "safe_guided_review",
                "message": (
                    "Pre-submission checks, data validation, and user approval passed successfully. "
                    "Automated external submissions are disabled (ENABLE_LIVE_SUBMISSIONS=false) for user safety. "
                    "Please visit the official employer portal using the link provided to finalize your submission."
                ),
                "official_url": job.url,
                "verified_answers": approval.answers,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            audit = AuditEvent(
                user_id=user_id,
                action="application_ready_for_user_submission",
                resource_type="application",
                resource_id=app.id,
                details=app.verification_details
            )
            db.add(audit)
            db.commit()
            db.refresh(app)
            return app

        # If live submissions are explicitly enabled in environment
        try:
            submission_result = await self.browser_service.submit_application_form(
                job_url=job.url,
                candidate_data={
                    "name": profile.full_name,
                    "email": profile.email,
                    "phone": profile.phone
                }
            )

            status = submission_result.get("status", ApplicationStatus.SUBMISSION_UNKNOWN.value)
            app.status = status
            app.verification_details = submission_result.get("verification_details", {})
            if status in [ApplicationStatus.SUBMITTED.value, ApplicationStatus.VERIFIED.value]:
                app.submitted_at = datetime.now(timezone.utc)
                app.submission_reference = submission_result.get("receipt_id")
            elif status == ApplicationStatus.NEEDS_USER_ACTION.value:
                app.error_message = submission_result.get("reason", "Manual user action required on portal.")

        except Exception as e:
            logger.error(f"Live submission failed: {e}")
            app.status = ApplicationStatus.FAILED.value
            app.error_message = str(e)

        audit = AuditEvent(
            user_id=user_id,
            action="application_submission_attempted",
            resource_type="application",
            resource_id=app.id,
            details={"status": app.status, "error": app.error_message}
        )
        db.add(audit)
        db.commit()
        db.refresh(app)
        return app

    def mark_manually_applied(
        self,
        db: Session,
        user_id: str,
        application_id: str,
        notes: Optional[str] = None,
        reference_id: Optional[str] = None
    ) -> Application:
        """
        Allows candidate to confirm they manually completed the application on the employer website.
        """
        app = db.query(Application).filter(
            Application.id == application_id,
            Application.user_id == user_id
        ).first()

        if not app:
            raise ApplicationServiceError("Application not found.")

        app.status = ApplicationStatus.MANUALLY_APPLIED.value
        app.submitted_at = datetime.now(timezone.utc)
        if reference_id:
            app.submission_reference = reference_id
        if notes:
            details = dict(app.verification_details or {})
            details["candidate_notes"] = notes
            app.verification_details = details

        audit = AuditEvent(
            user_id=user_id,
            action="application_manually_applied",
            resource_type="application",
            resource_id=app.id,
            details={"reference_id": reference_id, "notes": notes}
        )
        db.add(audit)
        db.commit()
        db.refresh(app)
        return app

    def list_applications(self, db: Session, user_id: str) -> List[Application]:
        return db.query(Application).filter(Application.user_id == user_id).order_by(Application.created_at.desc()).all()

    def get_application(self, db: Session, user_id: str, app_id: str) -> Optional[Application]:
        return db.query(Application).filter(
            Application.id == app_id,
            Application.user_id == user_id
        ).first()
