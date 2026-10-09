import logging
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models import Job
from app.schemas import JobOut, JobSearchResponse
from app.integrations.greenhouse import GreenhouseIntegration
from app.integrations.lever import LeverIntegration

logger = logging.getLogger(__name__)

class JobSearchService:
    def __init__(self):
        self.greenhouse = GreenhouseIntegration(timeout=4.0)
        self.lever = LeverIntegration(timeout=2.5)

    async def search_and_sync_jobs(
        self,
        db: Session,
        skills: Optional[List[str]] = None,
        location: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        limit: int = 10
    ) -> JobSearchResponse:
        """
        Retrieves real jobs from authorized public sources (Greenhouse, Lever),
        deduplicates against the database, updates/inserts records, and returns them.
        """
        all_fetched_jobs: List[Dict[str, Any]] = []
        errors: Dict[str, str] = {}
        sources_checked: List[str] = []

        # 1. Search sources concurrently
        sources_checked.append("greenhouse")
        sources_checked.append("lever")

        async def fetch_gh():
            try:
                return await self.greenhouse.search_jobs(
                    keywords=keywords or [],
                    location=location,
                    skills=skills or [],
                    limit=limit
                )
            except Exception as e:
                logger.warning(f"Greenhouse search error: {e}")
                errors["greenhouse"] = str(e)
                return []

        async def fetch_lever():
            try:
                return await self.lever.search_jobs(
                    keywords=keywords or [],
                    location=location,
                    skills=skills or [],
                    limit=limit
                )
            except Exception as e:
                logger.warning(f"Lever search error: {e}")
                errors["lever"] = str(e)
                return []

        gh_jobs, lever_jobs = await asyncio.gather(fetch_gh(), fetch_lever())
        all_fetched_jobs.extend(gh_jobs)
        all_fetched_jobs.extend(lever_jobs)

        # 3. Deduplicate and persist to DB
        synced_jobs: List[Job] = []
        seen_keys = set()

        for item in all_fetched_jobs:
            provider = item["provider"]
            ext_id = item["external_id"]
            dedup_key = (provider, ext_id)
            if dedup_key in seen_keys:
                continue
            seen_keys.add(dedup_key)

            # Query existing
            existing_job = db.query(Job).filter(
                Job.provider == provider,
                Job.external_id == ext_id
            ).first()

            if existing_job:
                # Refresh metadata
                existing_job.title = item["title"]
                existing_job.company = item["company"]
                existing_job.location = item["location"]
                existing_job.description = item["description"]
                existing_job.url = item["url"]
                existing_job.retrieved_at = datetime.now(timezone.utc)
                synced_jobs.append(existing_job)
            else:
                new_job = Job(
                    provider=provider,
                    external_id=ext_id,
                    company=item["company"],
                    title=item["title"],
                    location=item["location"],
                    description=item["description"],
                    salary=item.get("salary"),
                    job_type=item.get("job_type", "Full-time"),
                    url=item["url"],
                    retrieved_at=datetime.now(timezone.utc),
                    raw_data=item.get("raw_data", {})
                )
                db.add(new_job)
                synced_jobs.append(new_job)

        try:
            db.commit()
            for j in synced_jobs:
                db.refresh(j)
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to commit synced jobs to DB: {e}")

        # If live sources returned zero due to strict keyword/location match or network,
        # check if matching jobs exist in the database from earlier synchronizations.
        # Do NOT dump unrelated database records if specific search terms were requested.
        if not synced_jobs:
            query = db.query(Job)
            terms = (keywords or []) + (skills or [])
            if terms:
                filters = [Job.title.ilike(f"%{t}%") for t in terms[:5]] + [Job.description.ilike(f"%{t}%") for t in terms[:5]]
                synced_jobs = query.filter(or_(*filters)).limit(limit).all()
            else:
                # Only when no search terms were specified (general browsing), show recent jobs
                synced_jobs = db.query(Job).order_by(Job.retrieved_at.desc()).limit(limit).all()

        jobs_out = [JobOut.model_validate(j) for j in synced_jobs[:limit]]

        return JobSearchResponse(
            total_found=len(jobs_out),
            jobs=jobs_out,
            sources_checked=sources_checked,
            errors=errors
        )

    def get_job_by_id(self, db: Session, job_id: str) -> Optional[Job]:
        return db.query(Job).filter(Job.id == job_id).first()
