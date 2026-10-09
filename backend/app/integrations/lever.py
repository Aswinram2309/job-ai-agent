import logging
import asyncio
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import httpx

logger = logging.getLogger(__name__)

KNOWN_LEVER_COMPANIES = [
    "datadog"
]

class LeverIntegration:
    BASE_URL = "https://api.lever.co/v0/postings/{company}?mode=json"

    def __init__(self, timeout: float = 2.0):
        self.timeout = httpx.Timeout(timeout, connect=2.0)

    async def fetch_company_postings(self, company: str, client: Optional[httpx.AsyncClient] = None) -> List[Dict[str, Any]]:
        """
        Fetches live jobs for a given company from Lever public postings API.
        """
        url = self.BASE_URL.format(company=company)
        close_client = False
        if client is None:
            client = httpx.AsyncClient(timeout=self.timeout)
            close_client = True

        try:
            resp = await client.get(url)
            if resp.status_code == 404:
                logger.info(f"Lever company postings '{company}' not found (404).")
                return []
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list):
                return data
            return []
        except httpx.HTTPStatusError as e:
            logger.warning(f"Lever HTTP error for {company}: {e}")
            return []
        except Exception as e:
            logger.warning(f"Failed to fetch Lever postings for {company}: {e}")
            return []
        finally:
            if close_client:
                await client.aclose()

    async def search_jobs(
        self,
        keywords: List[str],
        location: Optional[str] = None,
        skills: Optional[List[str]] = None,
        limit: int = 10,
        companies: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieves real jobs across public Lever postings and filters by keywords, location, skills.
        """
        target_companies = companies or KNOWN_LEVER_COMPANIES[:3]
        normalized_results: List[Dict[str, Any]] = []

        search_terms = [k.lower() for k in (keywords or []) + (skills or [])]
        loc_term = location.lower() if location else None

        async with httpx.AsyncClient(timeout=httpx.Timeout(2.5, connect=1.5)) as client:
            company_tasks = [self.fetch_company_postings(c, client=client) for c in target_companies]
            company_results = await asyncio.gather(*company_tasks, return_exceptions=True)

            for company, postings in zip(target_companies, company_results):
                if isinstance(postings, Exception) or not isinstance(postings, list):
                    continue
                for item in postings:
                    job_id = str(item.get("id"))
                    title = item.get("text", "")
                    description_plain = item.get("descriptionPlain", "") or item.get("description", "")
                    categories = item.get("categories", {}) or {}
                    loc_name = categories.get("location", "")
                    commitment = categories.get("commitment", "Full-time")
                    job_url = item.get("hostedUrl", f"https://jobs.lever.co/{company}/{job_id}")

                    text_blob = f"{title} {loc_name} {description_plain}".lower()

                    if loc_term and loc_term not in text_blob and "remote" not in text_blob:
                        continue

                    if search_terms:
                        matches_keyword = any(term in text_blob for term in search_terms)
                        if not matches_keyword:
                            continue

                    normalized = {
                        "provider": "lever",
                        "external_id": f"lever_{company}_{job_id}",
                        "company": company.capitalize(),
                        "title": title,
                        "location": loc_name or "Remote / Unspecified",
                        "description": description_plain[:4000] if description_plain else title,
                        "salary": None,
                        "job_type": commitment or "Full-time",
                        "url": job_url,
                        "retrieved_at": datetime.now(timezone.utc),
                        "raw_data": {"company": company, "raw_id": job_id}
                    }
                    normalized_results.append(normalized)

                    if len(normalized_results) >= limit:
                        return normalized_results

        return normalized_results
