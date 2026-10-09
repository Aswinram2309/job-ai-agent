export interface User {
  id: string;
  email: string;
  full_name?: string;
  created_at: string;
}

export interface Token {
  access_token: string;
  token_type: string;
  user_id: string;
  email: string;
}

export interface WorkExperienceItem {
  company: string;
  title: string;
  duration?: string;
  responsibilities: string[];
}

export interface EducationItem {
  institution: string;
  degree: string;
  field_of_study?: string;
  graduation_year?: string;
}

export interface ProjectItem {
  name: string;
  description: string;
  technologies: string[];
}

export interface CertificationItem {
  name: string;
  issuer?: string;
  year?: string;
}

export interface CandidateProfile {
  id: string;
  user_id: string;
  full_name?: string;
  email?: string;
  phone?: string;
  location?: string;
  summary?: string;
  technical_skills: string[];
  soft_skills: string[];
  experience_years?: number;
  work_experience: WorkExperienceItem[];
  education: EducationItem[];
  projects: ProjectItem[];
  certifications: CertificationItem[];
  previous_job_titles: string[];
  preferred_roles: string[];
  preferred_locations: string[];
  missing_information: string[];
  version: number;
  updated_at: string;
}

export interface Job {
  id: string;
  provider: string;
  external_id: string;
  company: string;
  title: string;
  location?: string;
  description?: string;
  salary?: string;
  job_type?: string;
  url: string;
  retrieved_at: string;
}

export interface JobMatchResult {
  job: Job;
  match_score: number;
  reasons: string[];
  matching_skills: string[];
  missing_requirements: string[];
  source: string;
  last_checked: string;
}

export type ApplicationStatus =
  | 'discovered'
  | 'recommended'
  | 'saved'
  | 'ready_to_apply'
  | 'awaiting_approval'
  | 'approved'
  | 'submitting'
  | 'submitted'
  | 'verified'
  | 'failed'
  | 'needs_user_action'
  | 'manually_applied'
  | 'closed_or_unavailable'
  | 'submission_unknown';

export interface Application {
  id: string;
  user_id: string;
  job_id: string;
  job?: Job;
  status: ApplicationStatus;
  submission_reference?: string;
  resume_version?: number;
  application_url?: string;
  verification_details: Record<string, any>;
  error_message?: string;
  submitted_at?: string;
  created_at: string;
  updated_at: string;
}

export interface DashboardStats {
  has_resume: boolean;
  resume_status: string;
  skills_detected: number;
  total_jobs_found: number;
  recommended_jobs: number;
  saved_jobs: number;
  applications_submitted: number;
  applications_awaiting_action: number;
  recent_applications: {
    id: string;
    job_title: string;
    company: string;
    status: ApplicationStatus;
    submitted_at?: string;
  }[];
}

export interface AgentToolCallInfo {
  tool_name: string;
  arguments: Record<string, any>;
  result: any;
}

export interface AgentChatResponse {
  reply: string;
  tools_executed: AgentToolCallInfo[];
}
