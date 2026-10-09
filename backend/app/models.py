import enum
from datetime import datetime, timezone
import uuid
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, Text, DateTime, ForeignKey, JSON
)
from sqlalchemy.orm import relationship
from app.database import Base

def generate_uuid():
    return str(uuid.uuid4())

def utc_now():
    return datetime.now(timezone.utc)

class ApplicationStatus(str, enum.Enum):
    DISCOVERED = "discovered"
    RECOMMENDED = "recommended"
    SAVED = "saved"
    READY_TO_APPLY = "ready_to_apply"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    SUBMITTING = "submitting"
    SUBMITTED = "submitted"
    VERIFIED = "verified"
    FAILED = "failed"
    NEEDS_USER_ACTION = "needs_user_action"
    MANUALLY_APPLIED = "manually_applied"
    CLOSED_OR_UNAVAILABLE = "closed_or_unavailable"
    SUBMISSION_UNKNOWN = "submission_unknown"

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    profile = relationship("CandidateProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    resumes = relationship("Resume", back_populates="user", cascade="all, delete-orphan")
    matches = relationship("JobMatch", back_populates="user", cascade="all, delete-orphan")
    applications = relationship("Application", back_populates="user", cascade="all, delete-orphan")
    approvals = relationship("ApplicationApproval", back_populates="user", cascade="all, delete-orphan")
    audit_events = relationship("AuditEvent", back_populates="user", cascade="all, delete-orphan")

class CandidateProfile(Base):
    __tablename__ = "candidate_profiles"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), unique=True, nullable=False)
    full_name = Column(String, nullable=True)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    location = Column(String, nullable=True)
    summary = Column(Text, nullable=True)
    technical_skills = Column(JSON, default=list)
    soft_skills = Column(JSON, default=list)
    experience_years = Column(Float, nullable=True)
    work_experience = Column(JSON, default=list)
    education = Column(JSON, default=list)
    projects = Column(JSON, default=list)
    certifications = Column(JSON, default=list)
    previous_job_titles = Column(JSON, default=list)
    preferred_roles = Column(JSON, default=list)
    preferred_locations = Column(JSON, default=list)
    missing_information = Column(JSON, default=list)
    version = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    user = relationship("User", back_populates="profile")

class Resume(Base):
    __tablename__ = "resumes"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    file_type = Column(String, nullable=False)  # pdf or docx
    extracted_text = Column(Text, nullable=True)
    is_parsed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    user = relationship("User", back_populates="resumes")

class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, default=generate_uuid)
    provider = Column(String, index=True, nullable=False)  # greenhouse, lever, career_site
    external_id = Column(String, index=True, nullable=False)
    company = Column(String, index=True, nullable=False)
    title = Column(String, index=True, nullable=False)
    location = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    salary = Column(String, nullable=True)
    job_type = Column(String, nullable=True)  # Full-time, Remote, etc.
    url = Column(String, nullable=False)
    retrieved_at = Column(DateTime(timezone=True), default=utc_now)
    raw_data = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    matches = relationship("JobMatch", back_populates="job", cascade="all, delete-orphan")
    applications = relationship("Application", back_populates="job", cascade="all, delete-orphan")

class JobMatch(Base):
    __tablename__ = "job_matches"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    job_id = Column(String, ForeignKey("jobs.id"), nullable=False)
    match_score = Column(Float, nullable=False)  # 0 to 100
    matching_skills = Column(JSON, default=list)
    missing_skills = Column(JSON, default=list)
    reasons = Column(JSON, default=list)
    analyzed_at = Column(DateTime(timezone=True), default=utc_now)

    user = relationship("User", back_populates="matches")
    job = relationship("Job", back_populates="matches")

class ApplicationApproval(Base):
    __tablename__ = "application_approvals"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    job_id = Column(String, ForeignKey("jobs.id"), nullable=False)
    profile_version = Column(Integer, nullable=False)
    answers = Column(JSON, default=dict)
    approved_at = Column(DateTime(timezone=True), default=utc_now)

    user = relationship("User", back_populates="approvals")

class Application(Base):
    __tablename__ = "applications"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    job_id = Column(String, ForeignKey("jobs.id"), nullable=False)
    status = Column(String, default=ApplicationStatus.AWAITING_APPROVAL.value)
    submission_reference = Column(String, nullable=True)
    resume_version = Column(Integer, nullable=True)
    application_url = Column(String, nullable=True)
    verification_details = Column(JSON, default=dict)
    error_message = Column(Text, nullable=True)
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    user = relationship("User", back_populates="applications")
    job = relationship("Job", back_populates="applications")

class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    action = Column(String, nullable=False)
    resource_type = Column(String, nullable=False)
    resource_id = Column(String, nullable=True)
    details = Column(JSON, default=dict)
    timestamp = Column(DateTime(timezone=True), default=utc_now)

    user = relationship("User", back_populates="audit_events")
