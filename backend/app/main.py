import os
import shutil
from pathlib import Path
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.config import settings
from app.database import engine, get_db, Base
from app.models import (
    User, CandidateProfile, Resume, Job, JobMatch,
    Application, ApplicationApproval, ApplicationStatus, AuditEvent
)
from app.schemas import (
    UserRegister, UserLogin, Token, UserOut,
    ProfileOut, ProfileUpdate, ResumeAnalysisResponse, ResumeConfirmRequest,
    JobSearchRequest, JobSearchResponse, JobOut,
    JobMatchRequest, JobMatchResponse, JobMatchResult,
    ApplicationApprovalRequest, ApplicationSubmitRequest, ApplicationOut,
    ManualApplyRequest,
    AgentChatRequest, AgentChatResponse
)
from app.auth import hash_password, verify_password, create_access_token, get_current_user
from app.services.resume_parser import parse_resume_content, ResumeParserError, ScannedPdfError
from app.services.profile_analyzer import analyze_resume_text
from app.services.job_search import JobSearchService
from app.services.job_matcher import JobMatcherService
from app.services.application_service import (
    ApplicationService, ApplicationServiceError, DuplicateApplicationError,
    MissingApprovalError, IncompleteProfileError
)
from app.agent.orchestrator import JobAgentOrchestrator

# Initialize database schema
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.APP_NAME,
    description="Backend-only and Full-stack AI Job Application Agent powered by Google Gemini",
    version="1.0.0"
)

# CORS setup
allowed_origins = [settings.FRONTEND_ORIGIN, "http://localhost:3000", "http://127.0.0.1:3000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Services
job_search_service = JobSearchService()
job_matcher_service = JobMatcherService()
application_service = ApplicationService()

# ----------------- Health Check -----------------
@app.get("/health", tags=["System"])
def health_check():
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "gemini_model": settings.GEMINI_MODEL,
        "gemini_configured": bool(settings.GEMINI_API_KEY),
        "live_submissions_enabled": settings.ENABLE_LIVE_SUBMISSIONS,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

# ----------------- Authentication -----------------
@app.post("/api/auth/register", response_model=Token, tags=["Auth"])
def register(user_in: UserRegister, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == user_in.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists."
        )

    user = User(
        email=user_in.email,
        hashed_password=hash_password(user_in.password),
        full_name=user_in.full_name
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Create empty candidate profile
    profile = CandidateProfile(
        user_id=user.id,
        full_name=user.full_name,
        email=user.email,
        version=1
    )
    db.add(profile)
    db.commit()

    token = create_access_token(data={"sub": user.id, "email": user.email})
    return Token(access_token=token, user_id=user.id, email=user.email)

@app.post("/api/auth/login", response_model=Token, tags=["Auth"])
def login(login_in: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == login_in.email).first()
    if not user or not verify_password(login_in.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password."
        )

    token = create_access_token(data={"sub": user.id, "email": user.email})
    return Token(access_token=token, user_id=user.id, email=user.email)

# ----------------- Candidate Profile -----------------
@app.get("/api/profile", response_model=ProfileOut, tags=["Profile"])
def get_profile(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = db.query(CandidateProfile).filter(CandidateProfile.user_id == current_user.id).first()
    if not profile:
        profile = CandidateProfile(user_id=current_user.id, email=current_user.email, full_name=current_user.full_name)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile

@app.patch("/api/profile", response_model=ProfileOut, tags=["Profile"])
def update_profile(
    profile_update: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    profile = db.query(CandidateProfile).filter(CandidateProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Candidate profile not found.")

    update_dict = profile_update.model_dump(exclude_unset=True)
    # Serialize nested pydantic lists if provided
    for key in ["work_experience", "education", "projects", "certifications"]:
        if key in update_dict and update_dict[key] is not None:
            update_dict[key] = [
                item.model_dump() if hasattr(item, "model_dump") else item
                for item in update_dict[key]
            ]

    for field, val in update_dict.items():
        setattr(profile, field, val)

    profile.version += 1
    profile.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(profile)
    return profile

# ----------------- Resume Upload & Analysis -----------------
@app.post("/api/resumes/analyze", response_model=ResumeAnalysisResponse, tags=["Resumes"])
async def analyze_resume_endpoint(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    contents = await file.read()
    filename = file.filename or "resume.pdf"

    try:
        extracted_text, file_type = parse_resume_content(
            filename=filename,
            file_bytes=contents,
            max_size_mb=settings.MAX_UPLOAD_SIZE_MB
        )
    except ScannedPdfError as spe:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"OCR Required: {str(spe)}"
        )
    except ResumeParserError as pe:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(pe))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"File parsing failed: {str(e)}")

    # Store file locally
    saved_filename = f"{current_user.id}_{int(datetime.now(timezone.utc).timestamp())}_{filename}"
    file_path = os.path.join(settings.UPLOAD_DIR, saved_filename)
    try:
        with open(file_path, "wb") as f:
            f.write(contents)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to persist resume file: {str(e)}")

    # Run Gemini AI analysis
    try:
        extracted_profile = analyze_resume_text(extracted_text)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(ve))
    except RuntimeError as re:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(re))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Gemini analysis error: {str(e)}")

    # Create Resume record
    resume = Resume(
        user_id=current_user.id,
        filename=filename,
        file_path=file_path,
        file_size=len(contents),
        file_type=file_type,
        extracted_text=extracted_text,
        is_parsed=True
    )
    db.add(resume)

    # Automatically populate/sync CandidateProfile
    profile = db.query(CandidateProfile).filter(CandidateProfile.user_id == current_user.id).first()
    if profile:
        profile.full_name = extracted_profile.full_name or profile.full_name or current_user.full_name
        profile.email = extracted_profile.email or profile.email or current_user.email
        profile.phone = extracted_profile.phone or profile.phone
        profile.location = extracted_profile.location or profile.location
        profile.summary = extracted_profile.summary or profile.summary
        profile.technical_skills = extracted_profile.technical_skills
        profile.soft_skills = extracted_profile.soft_skills
        profile.experience_years = extracted_profile.experience_years
        profile.work_experience = [w.model_dump() for w in extracted_profile.work_experience]
        profile.education = [e.model_dump() for e in extracted_profile.education]
        profile.projects = [p.model_dump() for p in extracted_profile.projects]
        profile.certifications = [c.model_dump() for c in extracted_profile.certifications]
        profile.previous_job_titles = extracted_profile.previous_job_titles
        profile.preferred_roles = extracted_profile.preferred_roles
        profile.preferred_locations = extracted_profile.preferred_locations
        profile.missing_information = extracted_profile.missing_information
        profile.version += 1
        profile.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(resume)

    return ResumeAnalysisResponse(
        resume_id=resume.id,
        filename=filename,
        file_type=file_type,
        extracted_profile=extracted_profile,
        message="Resume successfully parsed and analyzed by Gemini"
    )

@app.post("/api/resumes/{resume_id}/confirm", response_model=ProfileOut, tags=["Resumes"])
def confirm_resume_profile(
    resume_id: str,
    req: ResumeConfirmRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    resume = db.query(Resume).filter(Resume.id == resume_id, Resume.user_id == current_user.id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found.")

    profile = db.query(CandidateProfile).filter(CandidateProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found.")

    update_dict = req.profile.model_dump(exclude_unset=True)
    for key in ["work_experience", "education", "projects", "certifications"]:
        if key in update_dict and update_dict[key] is not None:
            update_dict[key] = [
                item.model_dump() if hasattr(item, "model_dump") else item
                for item in update_dict[key]
            ]

    for field, val in update_dict.items():
        setattr(profile, field, val)

    profile.version += 1
    profile.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(profile)
    return profile

# ----------------- Job Search & Listings -----------------
@app.post("/api/jobs/search", response_model=JobSearchResponse, tags=["Jobs"])
async def search_jobs_endpoint(
    req: JobSearchRequest,
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    response = await job_search_service.search_and_sync_jobs(
        db=db,
        skills=req.skills,
        location=req.location,
        keywords=req.keywords,
        limit=req.limit
    )
    return response

@app.get("/api/jobs", response_model=List[JobOut], tags=["Jobs"])
def list_jobs(
    limit: int = Query(default=20, ge=1, le=100),
    q: Optional[str] = None,
    location: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Job)
    if q:
        query = query.filter(Job.title.ilike(f"%{q}%") | Job.company.ilike(f"%{q}%"))
    if location:
        query = query.filter(Job.location.ilike(f"%{location}%"))
    jobs = query.order_by(Job.retrieved_at.desc()).limit(limit).all()
    return jobs

@app.get("/api/jobs/{job_id}", response_model=JobOut, tags=["Jobs"])
def get_job_detail(job_id: str, db: Session = Depends(get_db)):
    job = job_search_service.get_job_by_id(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job with ID '{job_id}' not found.")
    return job

# ----------------- Job Matching -----------------
@app.post("/api/jobs/match", response_model=JobMatchResponse, tags=["Jobs"])
async def match_jobs_endpoint(
    req: JobMatchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    profile = db.query(CandidateProfile).filter(CandidateProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=400, detail="Candidate profile required before matching jobs.")

    query = db.query(Job)
    if req.job_ids:
        query = query.filter(Job.id.in_(req.job_ids))
    jobs = query.limit(req.limit or 10).all()

    if not jobs:
        return JobMatchResponse(matches=[], total_analyzed=0)

    matches = await job_matcher_service.rank_and_save_matches(
        db=db,
        user_id=current_user.id,
        profile=profile,
        jobs=jobs,
        min_score=req.min_score or 0.0,
        limit=req.limit or 10
    )
    return JobMatchResponse(matches=matches, total_analyzed=len(jobs))

# ----------------- Application Approval & Submissions -----------------
@app.post("/api/jobs/{job_id}/approve", tags=["Applications"])
def approve_job_application(
    job_id: str,
    req: ApplicationApprovalRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not req.confirmed:
        raise HTTPException(status_code=400, detail="Explicit confirmation is required to approve an application.")

    try:
        approval = application_service.record_approval(
            db=db,
            user_id=current_user.id,
            job_id=job_id,
            answers=req.answers
        )
        return {
            "status": "approved",
            "approval_id": approval.id,
            "job_id": job_id,
            "profile_version": approval.profile_version,
            "approved_at": approval.approved_at.isoformat(),
            "message": "Application approved by candidate and queued for submission."
        }
    except DuplicateApplicationError as da:
        raise HTTPException(status_code=409, detail=str(da))
    except (IncompleteProfileError, ApplicationServiceError) as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/applications/{application_id}/submit", response_model=ApplicationOut, tags=["Applications"])
async def submit_application_endpoint(
    application_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        app_record = await application_service.execute_submission(
            db=db,
            user_id=current_user.id,
            application_id=application_id
        )
        return app_record
    except MissingApprovalError as ma:
        raise HTTPException(status_code=403, detail=str(ma))
    except IncompleteProfileError as ip:
        raise HTTPException(status_code=422, detail=str(ip))
    except ApplicationServiceError as ae:
        raise HTTPException(status_code=400, detail=str(ae))

@app.post("/api/jobs/{job_id}/save", response_model=ApplicationOut, tags=["Applications"])
def save_job_endpoint(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        saved_app = application_service.save_job(db=db, user_id=current_user.id, job_id=job_id)
        return saved_app
    except ApplicationServiceError as ae:
        raise HTTPException(status_code=400, detail=str(ae))

@app.post("/api/applications/{application_id}/manual-apply", response_model=ApplicationOut, tags=["Applications"])
def manual_apply_endpoint(
    application_id: str,
    req: ManualApplyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        app_record = application_service.mark_manually_applied(
            db=db,
            user_id=current_user.id,
            application_id=application_id,
            notes=req.notes,
            reference_id=req.reference_id
        )
        return app_record
    except ApplicationServiceError as ae:
        raise HTTPException(status_code=400, detail=str(ae))

@app.get("/api/applications", response_model=List[ApplicationOut], tags=["Applications"])
def list_applications_endpoint(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return application_service.list_applications(db=db, user_id=current_user.id)

@app.get("/api/applications/{application_id}", response_model=ApplicationOut, tags=["Applications"])
def get_application_endpoint(
    application_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    app_record = application_service.get_application(db=db, user_id=current_user.id, app_id=application_id)
    if not app_record:
        raise HTTPException(status_code=404, detail="Application not found.")
    return app_record

# ----------------- Dashboard Statistics -----------------
@app.get("/api/dashboard/stats", tags=["Dashboard"])
def get_dashboard_stats(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = db.query(CandidateProfile).filter(CandidateProfile.user_id == current_user.id).first()
    resumes_count = db.query(Resume).filter(Resume.user_id == current_user.id).count()
    total_jobs = db.query(Job).count()
    matches_count = db.query(JobMatch).filter(JobMatch.user_id == current_user.id).count()
    
    apps = db.query(Application).filter(Application.user_id == current_user.id).all()
    submitted_count = sum(1 for a in apps if a.status in [ApplicationStatus.SUBMITTED.value, ApplicationStatus.VERIFIED.value, ApplicationStatus.MANUALLY_APPLIED.value])
    awaiting_action = sum(1 for a in apps if a.status in [
        ApplicationStatus.AWAITING_APPROVAL.value,
        ApplicationStatus.NEEDS_USER_ACTION.value,
        ApplicationStatus.READY_TO_APPLY.value,
        ApplicationStatus.APPROVED.value
    ])
    saved_count = sum(1 for a in apps if a.status == ApplicationStatus.SAVED.value)

    skills_detected = len(profile.technical_skills) if (profile and profile.technical_skills) else 0

    return {
        "has_resume": resumes_count > 0,
        "resume_status": "Parsed & Active" if resumes_count > 0 else "No Resume Uploaded",
        "skills_detected": skills_detected,
        "total_jobs_found": total_jobs,
        "recommended_jobs": matches_count,
        "saved_jobs": saved_count,
        "applications_submitted": submitted_count,
        "applications_awaiting_action": awaiting_action,
        "recent_applications": [
            {
                "id": a.id,
                "job_title": a.job.title if a.job else "Unknown",
                "company": a.job.company if a.job else "Unknown",
                "status": a.status,
                "submitted_at": a.submitted_at.isoformat() if a.submitted_at else None
            }
            for a in apps[:5]
        ]
    }

# ----------------- Agent Chat -----------------
@app.post("/api/agent/chat", response_model=AgentChatResponse, tags=["AI Agent"])
async def agent_chat_endpoint(
    req: AgentChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    orchestrator = JobAgentOrchestrator(db=db, user_id=current_user.id)
    response = await orchestrator.chat(
        user_message=req.message,
        session_history=req.session_history
    )
    return response

# ----------------- Account & Data Deletion -----------------
@app.delete("/api/account", tags=["Settings"])
def delete_user_account(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Clean up uploaded files
    user_resumes = db.query(Resume).filter(Resume.user_id == current_user.id).all()
    for r in user_resumes:
        if r.file_path and os.path.exists(r.file_path):
            try:
                os.remove(r.file_path)
            except Exception:
                pass

    db.delete(current_user)
    db.commit()
    return {"status": "success", "message": "All user data, resumes, and records have been permanently deleted."}
