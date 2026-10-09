import os
import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import (
    Base, User, CandidateProfile, Resume, Job, JobMatch,
    Application, ApplicationApproval, ApplicationStatus
)
from app.auth import hash_password, verify_password, create_access_token
from app.services.resume_parser import (
    validate_resume_file, extract_text_from_pdf, extract_text_from_docx,
    extract_text_from_txt, parse_resume_content,
    UnsupportedFormatError, EmptyFileError, ScannedPdfError
)
from app.schemas import ProfileExtractedData, JobSearchResponse
from app.services.job_matcher import JobMatcherService
from app.services.application_service import (
    ApplicationService, MissingApprovalError, DuplicateApplicationError, IncompleteProfileError
)
from app.services.verification_service import VerificationService

# In-memory SQLite for testing
TEST_DB_URL = "sqlite:///:memory:"

@pytest.fixture
def db_session():
    engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

# ----------------- 1. Auth & Password Hashing Tests -----------------
def test_password_hashing():
    pw = "SuperSecure123!"
    hashed = hash_password(pw)
    assert hashed != pw
    assert verify_password(pw, hashed) is True
    assert verify_password("WrongPassword", hashed) is False

def test_jwt_token_generation():
    token = create_access_token(data={"sub": "user_123", "email": "test@example.com"})
    assert isinstance(token, str)
    assert len(token) > 20

# ----------------- 2. Resume File Validation Tests -----------------
def test_validate_resume_file_pdf():
    pdf_bytes = b"%PDF-1.4 Mock content"
    ext = validate_resume_file("resume.pdf", pdf_bytes, max_size_mb=10)
    assert ext == "pdf"

def test_validate_resume_file_docx():
    docx_bytes = b"PK\x03\x04Mock zip docx content"
    ext = validate_resume_file("resume.docx", docx_bytes, max_size_mb=10)
    assert ext == "docx"

def test_validate_resume_invalid_extension():
    with pytest.raises(UnsupportedFormatError):
        validate_resume_file("resume.exe", b"binary", max_size_mb=10)

def test_validate_resume_empty_file():
    with pytest.raises(EmptyFileError):
        validate_resume_file("resume.pdf", b"", max_size_mb=10)

# ----------------- 3. Structured Profile Schema Validation -----------------
def test_profile_schema_validation():
    valid_data = {
        "full_name": "Jane Developer",
        "email": "jane@example.com",
        "technical_skills": ["Python", "FastAPI", "PostgreSQL"],
        "soft_skills": ["Communication"],
        "experience_years": 4.5,
        "work_experience": [
            {
                "company": "Tech Corp",
                "title": "Backend Engineer",
                "duration": "2020-Present",
                "responsibilities": ["API Development"]
            }
        ],
        "education": [
            {
                "institution": "MIT",
                "degree": "B.S. Computer Science",
                "graduation_year": "2020"
            }
        ],
        "missing_information": []
    }
    profile = ProfileExtractedData.model_validate(valid_data)
    assert profile.full_name == "Jane Developer"
    assert len(profile.technical_skills) == 3
    assert profile.experience_years == 4.5

# ----------------- 4. Job Deduplication & Storage -----------------
def test_job_deduplication(db_session):
    job1 = Job(
        provider="greenhouse",
        external_id="gh_12345",
        company="Cloudflare",
        title="Software Engineer",
        url="https://boards.greenhouse.io/cloudflare/jobs/12345"
    )
    db_session.add(job1)
    db_session.commit()

    # Querying by provider and external_id
    existing = db_session.query(Job).filter(
        Job.provider == "greenhouse",
        Job.external_id == "gh_12345"
    ).first()
    assert existing is not None
    assert existing.company == "Cloudflare"

# ----------------- 5. Deterministic Matching Algorithm -----------------
def test_deterministic_matching(db_session):
    matcher = JobMatcherService()

    profile = CandidateProfile(
        user_id="user_test",
        technical_skills=["Python", "FastAPI", "SQL", "Docker"],
        preferred_roles=["Backend Engineer"],
        location="Remote"
    )

    job = Job(
        provider="greenhouse",
        external_id="gh_888",
        company="Acme",
        title="Senior Backend Engineer",
        description="We require strong Python and FastAPI experience along with Docker containers.",
        location="Remote",
        url="https://example.com/job/888"
    )

    result = matcher.calculate_deterministic_match(profile, job)
    assert result["score"] >= 60.0  # High score due to skill, title, and remote overlap
    assert "python" in [s.lower() for s in result["matching_skills"]]
    assert "fastapi" in [s.lower() for s in result["matching_skills"]]

# ----------------- 6. Application Consent & Duplicate Guardrail -----------------
def test_application_consent_and_duplicates(db_session):
    app_service = ApplicationService()

    # Setup user and profile
    user = User(email="applicant@example.com", hashed_password="hash_value_123")
    db_session.add(user)
    db_session.commit()

    profile = CandidateProfile(user_id=user.id, email=user.email, version=1)
    db_session.add(profile)

    job = Job(
        provider="greenhouse",
        external_id="gh_999",
        company="Stripe",
        title="Staff Engineer",
        url="https://example.com/stripe/999"
    )
    db_session.add(job)
    db_session.commit()

    # 1. Approval recorded
    approval = app_service.record_approval(db_session, user.id, job.id, answers={"sponsorship": "No"})
    assert approval is not None
    assert approval.profile_version == 1

    # Check application created with APPROVED status
    app_record = db_session.query(Application).filter(Application.user_id == user.id, Application.job_id == job.id).first()
    assert app_record is not None
    assert app_record.status == ApplicationStatus.APPROVED.value

    # Set status to submitted to test duplicate prevention
    app_record.status = ApplicationStatus.SUBMITTED.value
    db_session.commit()

    with pytest.raises(DuplicateApplicationError):
        app_service.record_approval(db_session, user.id, job.id, answers={})

def test_missing_approval_rejection(db_session):
    app_service = ApplicationService()
    user = User(email="unapproved@example.com", hashed_password="hash_value_123")
    db_session.add(user)
    db_session.commit()

    job = Job(provider="greenhouse", external_id="gh_111", company="GitLab", title="DevOps", url="https://gitlab.com")
    db_session.add(job)
    db_session.commit()

    # Create unapproved application
    unapproved_app = Application(user_id=user.id, job_id=job.id, status=ApplicationStatus.DISCOVERED.value)
    db_session.add(unapproved_app)
    db_session.commit()

    import asyncio
    with pytest.raises(MissingApprovalError):
        asyncio.run(app_service.execute_submission(db_session, user.id, unapproved_app.id))

# ----------------- 7. Verification Service Receipts -----------------
def test_verification_service():
    verifier = VerificationService()

    # Greenhouse receipt check
    is_ver, status_str, evidence = verifier.verify_provider_receipt("greenhouse", {"id": "appl_839210"})
    assert is_ver is True
    assert status_str == "verified"
    assert evidence["receipt_id"] == "appl_839210"

    # Incomplete receipt
    is_ver, status_str, evidence = verifier.verify_provider_receipt("greenhouse", {})
    assert is_ver is False
    assert status_str == "submission_unknown"

# ----------------- 8. Plain Text Resume & Scanned PDF Tests -----------------
def test_validate_and_parse_txt_resume():
    txt_bytes = "John Engineer\nSkills: Python, FastAPI, Docker\nExperience: 5 years".encode("utf-8")
    ext = validate_resume_file("resume.txt", txt_bytes, max_size_mb=5)
    assert ext == "txt"

    text, detected_type = parse_resume_content("resume.txt", txt_bytes)
    assert detected_type == "txt"
    assert "FastAPI" in text

def test_empty_txt_resume_raises_error():
    with pytest.raises(EmptyFileError):
        parse_resume_content("resume.txt", b"   ")

# ----------------- 9. Save Job & Manual Apply Tests -----------------
def test_save_job(db_session):
    app_service = ApplicationService()
    user = User(email="saver@example.com", hashed_password="hash_value_123")
    db_session.add(user)
    db_session.commit()

    job = Job(provider="greenhouse", external_id="gh_saved_1", company="Vercel", title="Frontend Engineer", url="https://vercel.com/job/1")
    db_session.add(job)
    db_session.commit()

    saved_app = app_service.save_job(db_session, user.id, job.id)
    assert saved_app.status == ApplicationStatus.SAVED.value
    assert saved_app.job_id == job.id

def test_manual_apply_workflow(db_session):
    app_service = ApplicationService()
    user = User(email="manual@example.com", hashed_password="hash_value_123")
    db_session.add(user)
    db_session.commit()

    job = Job(provider="lever", external_id="lever_manual_1", company="Linear", title="Fullstack", url="https://linear.app/careers/1")
    db_session.add(job)
    db_session.commit()

    app = Application(user_id=user.id, job_id=job.id, status=ApplicationStatus.READY_TO_APPLY.value)
    db_session.add(app)
    db_session.commit()

    updated = app_service.mark_manually_applied(
        db_session, user.id, app.id, notes="Submitted on Linear official site", reference_id="REF-12345"
    )
    assert updated.status == ApplicationStatus.MANUALLY_APPLIED.value
    assert updated.submission_reference == "REF-12345"
    assert updated.submitted_at is not None

# ----------------- 10. Truth-in-Status: No False Verified Submission -----------------
def test_safe_guided_review_not_marked_submitted(db_session):
    """
    Verifies that when live automated submissions are disabled, the system transitions to
    READY_TO_APPLY and DOES NOT claim the application was successfully submitted or verified.
    """
    app_service = ApplicationService()
    user = User(email="honest@example.com", hashed_password="hash_value_123")
    db_session.add(user)
    db_session.commit()

    profile = CandidateProfile(user_id=user.id, email=user.email, version=1)
    db_session.add(profile)

    job = Job(provider="greenhouse", external_id="gh_safe_1", company="Supabase", title="DB Admin", url="https://supabase.com/careers")
    db_session.add(job)
    db_session.commit()

    # Record approval
    approval = app_service.record_approval(db_session, user.id, job.id, answers={"relocate": "yes"})
    app_record = db_session.query(Application).filter(Application.user_id == user.id, Application.job_id == job.id).first()

    import asyncio
    result_app = asyncio.run(app_service.execute_submission(db_session, user.id, app_record.id))

    # CRITICAL: Must be READY_TO_APPLY, never SUBMITTED or VERIFIED without live confirmation
    assert result_app.status == ApplicationStatus.READY_TO_APPLY.value
    assert result_app.submitted_at is None
    assert result_app.submission_reference is None
    assert result_app.verification_details.get("mode") == "safe_guided_review"
