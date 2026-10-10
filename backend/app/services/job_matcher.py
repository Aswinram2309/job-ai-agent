import logging
import json
import asyncio
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from google import genai
from google.genai import types

from app.config import settings
from app.models import Job, JobMatch, CandidateProfile
from app.schemas import JobMatchResult, JobOut

logger = logging.getLogger(__name__)

class JobMatcherService:
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.model = settings.GEMINI_MODEL

    def calculate_deterministic_match(
        self,
        profile: CandidateProfile,
        job: Job
    ) -> Dict[str, Any]:
        """
        Calculates a deterministic baseline score (0-100) based on skill intersection,
        title overlap, and location preferences.
        """
        cand_skills = set(s.lower() for s in (profile.technical_skills or []))
        job_text = f"{job.title} {job.description}".lower()

        matching_skills = []
        missing_skills = []

        # Check detected profile skills in job
        for skill in cand_skills:
            if skill in job_text:
                matching_skills.append(skill)

        # Keyword heuristics from job title and common requirements
        common_tech = ["python", "fastapi", "react", "next.js", "docker", "kubernetes", "sql", "postgresql", "typescript", "aws", "gcp"]
        for tech in common_tech:
            if tech in job_text and tech not in cand_skills and tech not in missing_skills:
                missing_skills.append(tech)

        # Base skill coverage
        skill_score = (len(matching_skills) / max(len(matching_skills) + len(missing_skills), 1)) * 50

        # Title / Role match (30%)
        title_score = 0
        pref_roles = [r.lower() for r in (profile.preferred_roles or [])] + [t.lower() for t in (profile.previous_job_titles or [])]
        if any(role in job.title.lower() for role in pref_roles):
            title_score = 30
        elif any(word in job.title.lower() for word in ["developer", "engineer", "software", "backend", "full stack"]):
            title_score = 20

        # Location preference (20%)
        loc_score = 10
        if "remote" in job.location.lower() or "remote" in job_text:
            loc_score = 20
        elif profile.location and profile.location.lower() in job.location.lower():
            loc_score = 20

        total_score = min(round(skill_score + title_score + loc_score, 1), 100.0)

        reasons = [
            f"Matched {len(matching_skills)} skills: {', '.join(matching_skills[:5]) if matching_skills else 'general technical overlap'}.",
            f"Role relevance score for '{job.title}'.",
            f"Location match: {job.location}."
        ]

        return {
            "score": total_score,
            "matching_skills": matching_skills,
            "missing_skills": missing_skills[:5],
            "reasons": reasons
        }

    async def match_job_with_gemini(
        self,
        profile: CandidateProfile,
        job: Job
    ) -> Dict[str, Any]:
        """
        Uses Gemini to semantically evaluate job alignment and explain match reasons.
        Falls back smoothly to deterministic scoring if API fails.
        """
        baseline = self.calculate_deterministic_match(profile, job)

        if not self.api_key:
            return baseline

        prompt = f"""You are an expert Job Matching AI Engine.
Evaluate the match between this candidate profile and job posting.

CANDIDATE:
- Skills: {profile.technical_skills}
- Experience Years: {profile.experience_years}
- Preferred Roles: {profile.preferred_roles}
- Location: {profile.location}
- Summary: {profile.summary}

JOB:
- Title: {job.title}
- Company: {job.company}
- Location: {job.location}
- Description excerpt: {job.description[:1200]}

Provide JSON with:
- "score": number between 0 and 100 representing ranking heuristic
- "matching_skills": list of candidate skills required by this job
- "missing_requirements": list of requirements mentioned in the job that candidate appears to lack
- "reasons": list of 2-3 specific objective sentences explaining the match alignment
"""

        candidate_models = [self.model]
        for m in ["gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.5-flash", "gemini-3.5-flash-lite", "gemini-flash-latest"]:
            if m not in candidate_models:
                candidate_models.append(m)

        client = genai.Client(api_key=self.api_key)

        def _call_gemini(m_name: str):
            return client.models.generate_content(
                model=m_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.1
                )
            )

        for model_name in candidate_models:
            try:
                resp = await asyncio.to_thread(_call_gemini, model_name)
                if resp.text:
                    ai_data = json.loads(resp.text)
                    return {
                        "score": float(ai_data.get("score", baseline["score"])),
                        "matching_skills": ai_data.get("matching_skills", baseline["matching_skills"]),
                        "missing_skills": ai_data.get("missing_requirements", baseline["missing_skills"]),
                        "reasons": ai_data.get("reasons", baseline["reasons"])
                    }
            except Exception as e:
                err_str = str(e)
                if "RESOURCE_EXHAUSTED" in err_str or "Quota exceeded" in err_str or "404" in err_str or "503" in err_str:
                    logger.warning(f"Job matching fallback: {model_name} unavailable ({err_str[:60]}). Trying next...")
                    continue
                logger.warning(f"Gemini job match evaluation failed: {e}")
                break

        return baseline

    async def rank_and_save_matches(
        self,
        db: Session,
        user_id: str,
        profile: CandidateProfile,
        jobs: List[Job],
        min_score: float = 0.0,
        limit: int = 10
    ) -> List[JobMatchResult]:
        """
        Scores candidate against a list of jobs, persists the results in JobMatch, and returns top ranked results.
        Uses deterministic baseline for fast pre-filtering, then deep Gemini evaluation on top candidates.
        """
        # Step 1: Pre-score with deterministic heuristics
        candidates_with_baseline = []
        for job in jobs:
            base = self.calculate_deterministic_match(profile, job)
            if base["score"] >= min_score:
                candidates_with_baseline.append((job, base))

        # Sort descending by preliminary score
        candidates_with_baseline.sort(key=lambda x: x[1]["score"], reverse=True)
        top_candidates = candidates_with_baseline[:limit]

        # Step 2: Semantic evaluation with Gemini on top matches in parallel
        async def evaluate_single(job_obj, base_data):
            try:
                match_data = await self.match_job_with_gemini(profile, job_obj)
                return job_obj, match_data
            except Exception as e:
                logger.warning(f"Error evaluating match for {job_obj.id}: {e}")
                return job_obj, base_data

        eval_tasks = [evaluate_single(j, b) for j, b in top_candidates]
        evaluated_pairs = await asyncio.gather(*eval_tasks, return_exceptions=False)

        results: List[JobMatchResult] = []

        for job, match_data in evaluated_pairs:
            score = match_data["score"]

            # Check or create JobMatch in DB
            existing_match = db.query(JobMatch).filter(
                JobMatch.user_id == user_id,
                JobMatch.job_id == job.id
            ).first()

            if existing_match:
                existing_match.match_score = score
                existing_match.matching_skills = match_data["matching_skills"]
                existing_match.missing_skills = match_data["missing_skills"]
                existing_match.reasons = match_data["reasons"]
                existing_match.analyzed_at = datetime.now(timezone.utc)
            else:
                new_match = JobMatch(
                    user_id=user_id,
                    job_id=job.id,
                    match_score=score,
                    matching_skills=match_data["matching_skills"],
                    missing_skills=match_data["missing_skills"],
                    reasons=match_data["reasons"],
                    analyzed_at=datetime.now(timezone.utc)
                )
                db.add(new_match)

            results.append(
                JobMatchResult(
                    job=JobOut.model_validate(job),
                    match_score=score,
                    reasons=match_data["reasons"],
                    matching_skills=match_data["matching_skills"],
                    missing_requirements=match_data["missing_skills"],
                    source=job.provider,
                    last_checked=job.retrieved_at
                )
            )

        try:
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to commit job matches: {e}")

        # Sort descending by match score
        results.sort(key=lambda x: x.match_score, reverse=True)
        return results[:limit]
