import logging
import asyncio
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.models import CandidateProfile, Job, Application, ApplicationApproval
from app.services.profile_analyzer import analyze_resume_text
from app.services.job_search import JobSearchService
from app.services.job_matcher import JobMatcherService
from app.services.application_service import ApplicationService

logger = logging.getLogger(__name__)

class AgentToolRegistry:
    def __init__(self, db: Session, user_id: str):
        self.db = db
        self.user_id = user_id
        self.job_search_service = JobSearchService()
        self.job_matcher_service = JobMatcherService()
        self.application_service = ApplicationService()
        self.executed_tools: List[Dict[str, Any]] = []

    def _record(self, name: str, args: Dict[str, Any], result: Any):
        self.executed_tools.append({
            "tool_name": name,
            "arguments": args,
            "result": result
        })

    def analyze_resume(self, resume_text: str) -> Dict[str, Any]:
        """
        Extracts structured candidate profile data from resume text using Gemini.
        Returns validated technical skills, experience, education, and missing information.
        """
        try:
            profile_data = analyze_resume_text(resume_text)
            res = profile_data.model_dump()
            self._record("analyze_resume", {"text_length": len(resume_text)}, res)
            return res
        except Exception as e:
            err = {"error": f"Failed to analyze resume: {str(e)}"}
            self._record("analyze_resume", {}, err)
            return err

    def search_jobs(
        self,
        keywords: Optional[List[str]] = None,
        location: Optional[str] = None,
        skills: Optional[List[str]] = None,
        limit: int = 5
    ) -> Dict[str, Any]:
        """
        Searches real, live job listings from authorized public boards (Greenhouse, Lever).
        Never fabricates listings.
        """
        kw = keywords or []
        sk = skills or []
        lim = min(max(limit, 1), 20)

        # Handle async search from sync tool
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # In running event loop (e.g. inside FastAPI request)
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    resp = pool.submit(
                        asyncio.run,
                        self.job_search_service.search_and_sync_jobs(
                            self.db, skills=sk, location=location, keywords=kw, limit=lim
                        )
                    ).result()
            else:
                resp = asyncio.run(
                    self.job_search_service.search_and_sync_jobs(
                        self.db, skills=sk, location=location, keywords=kw, limit=lim
                    )
                )
            data = resp.model_dump()
            self._record("search_jobs", {"keywords": kw, "location": location, "limit": lim}, data)
            return data
        except Exception as e:
            err = {"error": f"Job search failed: {str(e)}", "jobs": [], "total_found": 0}
            self._record("search_jobs", {"keywords": kw}, err)
            return err

    def match_jobs(self, job_ids: Optional[List[str]] = None, min_score: float = 0.0) -> Dict[str, Any]:
        """
        Scores candidate profile against available jobs and ranks them with explanation reasons.
        """
        profile = self.db.query(CandidateProfile).filter(CandidateProfile.user_id == self.user_id).first()
        if not profile:
            res = {"error": "No candidate profile found. Upload a resume first."}
            self._record("match_jobs", {}, res)
            return res

        query = self.db.query(Job)
        if job_ids:
            query = query.filter(Job.id.in_(job_ids))
        jobs = query.limit(10).all()

        if not jobs:
            res = {"matches": [], "message": "No jobs found to match against. Please search jobs first."}
            self._record("match_jobs", {}, res)
            return res

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    matches = pool.submit(
                        asyncio.run,
                        self.job_matcher_service.rank_and_save_matches(
                            self.db, self.user_id, profile, jobs, min_score=min_score, limit=5
                        )
                    ).result()
            else:
                matches = asyncio.run(
                    self.job_matcher_service.rank_and_save_matches(
                        self.db, self.user_id, profile, jobs, min_score=min_score, limit=5
                    )
                )

            data = {"matches": [m.model_dump() for m in matches], "total_matches": len(matches)}
            self._record("match_jobs", {"min_score": min_score}, data)
            return data
        except Exception as e:
            err = {"error": f"Job matching error: {str(e)}"}
            self._record("match_jobs", {}, err)
            return err

    def get_job_details(self, job_id: str) -> Dict[str, Any]:
        """
        Retrieves complete job posting details including title, company, description, and original URL.
        """
        job = self.job_search_service.get_job_by_id(self.db, job_id)
        if not job:
            res = {"error": f"Job ID '{job_id}' not found."}
            self._record("get_job_details", {"job_id": job_id}, res)
            return res

        data = {
            "id": job.id,
            "title": job.title,
            "company": job.company,
            "location": job.location,
            "description": job.description,
            "salary": job.salary,
            "url": job.url,
            "provider": job.provider,
            "retrieved_at": job.retrieved_at.isoformat() if job.retrieved_at else None
        }
        self._record("get_job_details", {"job_id": job_id}, data)
        return data

    def request_application_approval(self, job_id: str, answers: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Requests explicit user confirmation to apply for a specific job.
        Does NOT submit the application without user approval.
        """
        try:
            approval = self.application_service.record_approval(
                self.db, self.user_id, job_id, answers or {}
            )
            job = self.db.query(Job).filter(Job.id == job_id).first()
            data = {
                "approval_id": approval.id,
                "job_id": job_id,
                "job_title": job.title if job else "",
                "company": job.company if job else "",
                "status": "awaiting_user_confirmation",
                "message": (
                    f"Approval recorded for '{job.title if job else job_id}'. "
                    "Explicit confirmation is logged in the system before submission."
                )
            }
            self._record("request_application_approval", {"job_id": job_id}, data)
            return data
        except Exception as e:
            err = {"error": str(e)}
            self._record("request_application_approval", {"job_id": job_id}, err)
            return err

    def execute_approved_application(self, application_id: str) -> Dict[str, Any]:
        """
        Executes a previously approved application submission through authorized API or browser automation.
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    app = pool.submit(
                        asyncio.run,
                        self.application_service.execute_submission(self.db, self.user_id, application_id)
                    ).result()
            else:
                app = asyncio.run(
                    self.application_service.execute_submission(self.db, self.user_id, application_id)
                )

            data = {
                "application_id": app.id,
                "status": app.status,
                "submission_reference": app.submission_reference,
                "verification_details": app.verification_details,
                "submitted_at": app.submitted_at.isoformat() if app.submitted_at else None
            }
            self._record("execute_approved_application", {"application_id": application_id}, data)
            return data
        except Exception as e:
            err = {"error": str(e)}
            self._record("execute_approved_application", {"application_id": application_id}, err)
            return err

    def check_application_status(self, application_id: str) -> Dict[str, Any]:
        """
        Checks the live status, verification receipt, and audit history of an application.
        """
        app = self.application_service.get_application(self.db, self.user_id, application_id)
        if not app:
            res = {"error": f"Application '{application_id}' not found."}
            self._record("check_application_status", {"application_id": application_id}, res)
            return res

        data = {
            "application_id": app.id,
            "status": app.status,
            "submission_reference": app.submission_reference,
            "verification_details": app.verification_details,
            "error_message": app.error_message,
            "submitted_at": app.submitted_at.isoformat() if app.submitted_at else None,
            "updated_at": app.updated_at.isoformat() if app.updated_at else None
        }
        self._record("check_application_status", {"application_id": application_id}, data)
        return data

    def save_job(self, job_id: str) -> Dict[str, Any]:
        """
        Saves a job listing to candidate's tracked jobs list for later review.
        """
        try:
            app = self.application_service.save_job(self.db, self.user_id, job_id)
            res = {"application_id": app.id, "job_id": job_id, "status": app.status, "message": "Job saved successfully."}
            self._record("save_job", {"job_id": job_id}, res)
            return res
        except Exception as e:
            res = {"error": str(e)}
            self._record("save_job", {"job_id": job_id}, res)
            return res

    def mark_manually_applied(self, application_id: str, notes: Optional[str] = None) -> Dict[str, Any]:
        """
        Marks an application as manually submitted by candidate on the external employer site.
        """
        try:
            app = self.application_service.mark_manually_applied(self.db, self.user_id, application_id, notes=notes)
            res = {"application_id": app.id, "status": app.status, "message": "Application marked as manually applied."}
            self._record("mark_manually_applied", {"application_id": application_id}, res)
            return res
        except Exception as e:
            res = {"error": str(e)}
            self._record("mark_manually_applied", {"application_id": application_id}, res)
            return res
