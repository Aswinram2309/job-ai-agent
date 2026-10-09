from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, EmailStr, Field, ConfigDict

# ----------------- Auth Schemas -----------------
class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    full_name: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str

class UserOut(BaseModel):
    id: str
    email: str
    full_name: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# ----------------- Profile & Resume Schemas -----------------
class WorkExperienceItem(BaseModel):
    company: str = ""
    title: str = ""
    duration: Optional[str] = None
    responsibilities: List[str] = Field(default_factory=list)

class EducationItem(BaseModel):
    institution: str = ""
    degree: str = ""
    field_of_study: Optional[str] = None
    graduation_year: Optional[str] = None

class ProjectItem(BaseModel):
    name: str = ""
    description: str = ""
    technologies: List[str] = Field(default_factory=list)

class CertificationItem(BaseModel):
    name: str = ""
    issuer: Optional[str] = None
    year: Optional[str] = None

class ProfileExtractedData(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    summary: Optional[str] = None
    technical_skills: List[str] = Field(default_factory=list)
    soft_skills: List[str] = Field(default_factory=list)
    experience_years: Optional[float] = None
    work_experience: List[WorkExperienceItem] = Field(default_factory=list)
    education: List[EducationItem] = Field(default_factory=list)
    projects: List[ProjectItem] = Field(default_factory=list)
    certifications: List[CertificationItem] = Field(default_factory=list)
    previous_job_titles: List[str] = Field(default_factory=list)
    preferred_roles: List[str] = Field(default_factory=list)
    preferred_locations: List[str] = Field(default_factory=list)
    missing_information: List[str] = Field(default_factory=list)

class ProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    summary: Optional[str] = None
    technical_skills: Optional[List[str]] = None
    soft_skills: Optional[List[str]] = None
    experience_years: Optional[float] = None
    work_experience: Optional[List[WorkExperienceItem]] = None
    education: Optional[List[EducationItem]] = None
    projects: Optional[List[ProjectItem]] = None
    certifications: Optional[List[CertificationItem]] = None
    preferred_roles: Optional[List[str]] = None
    preferred_locations: Optional[List[str]] = None

class ProfileOut(BaseModel):
    id: str
    user_id: str
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    summary: Optional[str] = None
    technical_skills: List[str] = Field(default_factory=list)
    soft_skills: List[str] = Field(default_factory=list)
    experience_years: Optional[float] = None
    work_experience: List[Dict[str, Any]] = Field(default_factory=list)
    education: List[Dict[str, Any]] = Field(default_factory=list)
    projects: List[Dict[str, Any]] = Field(default_factory=list)
    certifications: List[Dict[str, Any]] = Field(default_factory=list)
    previous_job_titles: List[str] = Field(default_factory=list)
    preferred_roles: List[str] = Field(default_factory=list)
    preferred_locations: List[str] = Field(default_factory=list)
    missing_information: List[str] = Field(default_factory=list)
    version: int
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ResumeAnalysisResponse(BaseModel):
    resume_id: str
    filename: str
    file_type: str
    extracted_profile: ProfileExtractedData
    message: str = "Resume successfully analyzed"

class ResumeConfirmRequest(BaseModel):
    profile: ProfileUpdate

# ----------------- Job Schemas -----------------
class JobSearchRequest(BaseModel):
    skills: List[str] = Field(default_factory=list)
    location: Optional[str] = None
    keywords: List[str] = Field(default_factory=list)
    limit: int = Field(default=10, ge=1, le=50)

class JobOut(BaseModel):
    id: str
    provider: str
    external_id: str
    company: str
    title: str
    location: Optional[str] = None
    description: Optional[str] = None
    salary: Optional[str] = None
    job_type: Optional[str] = None
    url: str
    retrieved_at: datetime

    model_config = ConfigDict(from_attributes=True)

class JobSearchResponse(BaseModel):
    total_found: int
    jobs: List[JobOut]
    sources_checked: List[str]
    errors: Dict[str, str] = Field(default_factory=dict)

# ----------------- Job Matching Schemas -----------------
class JobMatchRequest(BaseModel):
    job_ids: Optional[List[str]] = None
    min_score: Optional[float] = 0.0
    limit: Optional[int] = 10

class JobMatchResult(BaseModel):
    job: JobOut
    match_score: float  # 0 to 100
    reasons: List[str]
    matching_skills: List[str]
    missing_requirements: List[str]
    source: str
    last_checked: datetime

class JobMatchResponse(BaseModel):
    matches: List[JobMatchResult]
    total_analyzed: int

# ----------------- Application Schemas -----------------
class ApplicationApprovalRequest(BaseModel):
    answers: Dict[str, Any] = Field(default_factory=dict)
    confirmed: bool = True

class ApplicationSubmitRequest(BaseModel):
    answers: Optional[Dict[str, Any]] = None

class ApplicationOut(BaseModel):
    id: str
    user_id: str
    job_id: str
    job: Optional[JobOut] = None
    status: str
    submission_reference: Optional[str] = None
    resume_version: Optional[int] = None
    application_url: Optional[str] = None
    verification_details: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None
    submitted_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ManualApplyRequest(BaseModel):
    notes: Optional[str] = None
    application_url: Optional[str] = None
    reference_id: Optional[str] = None

# ----------------- Agent Chat Schemas -----------------
class AgentChatRequest(BaseModel):
    message: str
    session_history: Optional[List[Dict[str, str]]] = Field(default_factory=list)

class AgentToolCallInfo(BaseModel):
    tool_name: str
    arguments: Dict[str, Any]
    result: Any

class AgentChatResponse(BaseModel):
    reply: str
    tools_executed: List[AgentToolCallInfo] = Field(default_factory=list)
