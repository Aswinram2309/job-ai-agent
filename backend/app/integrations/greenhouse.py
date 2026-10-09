import logging
import asyncio
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import httpx

logger = logging.getLogger(__name__)

# Representative active technology companies using public Greenhouse boards categorized by industry
GAMING_BOARDS = [
    "epicgames",
    "riotgames",
    "roblox",
    "discord",
    "bungie"
]

CREATIVE_DESIGN_BOARDS = [
    "figma",
    "pinterest",
    "airbnb",
    "roblox",
    "discord",
    "epicgames"
]

TECH_ENTERPRISE_BOARDS = [
    "stripe",
    "brex",
    "coinbase",
    "reddit",
    "gusto",
    "instacart"
]

INFRA_CLOUD_BOARDS = [
    "cloudflare",
    "canonical",
    "github",
    "gitlab",
    "elastic",
    "hashicorp"
]

ALL_KNOWN_GREENHOUSE_BOARDS = list(dict.fromkeys(
    GAMING_BOARDS + CREATIVE_DESIGN_BOARDS + TECH_ENTERPRISE_BOARDS + INFRA_CLOUD_BOARDS
))
KNOWN_GREENHOUSE_BOARDS = ALL_KNOWN_GREENHOUSE_BOARDS


def select_greenhouse_boards(
    keywords: Optional[List[str]] = None,
    skills: Optional[List[str]] = None
) -> List[str]:
    """
    Intelligently select relevant Greenhouse employer boards based on candidate
    keywords and skills domain.
    """
    combined = " ".join((keywords or []) + (skills or [])).lower()
    selected: List[str] = []

    # Gaming & 3D & Engine keywords
    if any(k in combined for k in ["game", "unity", "unreal", "3d", "level", "gameplay", "shader", "play", "animation", "r&d"]):
        selected.extend(GAMING_BOARDS)

    # Design / Creative / UI / UX
    if any(k in combined for k in ["design", "ui", "ux", "product design", "creative", "artist", "graphic", "visual"]):
        selected.extend(CREATIVE_DESIGN_BOARDS)

    # Cloud / Infra / Systems / Security / DevOps
    if any(k in combined for k in ["cloud", "infra", "devops", "kubernetes", "network", "distributed", "security", "linux", "scale", "sre"]):
        selected.extend(INFRA_CLOUD_BOARDS)

    # General tech / software / frontend / web / fullstack / finance
    if any(k in combined for k in ["software", "frontend", "fullstack", "react", "node", "python", "engineer", "finance", "data", "mobile"]):
        selected.extend(TECH_ENTERPRISE_BOARDS)
        selected.extend(INFRA_CLOUD_BOARDS[:2])

    # Default balanced set if no category detected
    if not selected:
        selected = ["epicgames", "riotgames", "stripe", "figma", "cloudflare", "roblox", "discord", "brex"]

    # Deduplicate while preserving category priority
    seen = set()
    result = []
    for b in selected:
        if b not in seen:
            seen.add(b)
            result.append(b)
    return result[:8]


class GreenhouseIntegration:
    BASE_URL = "https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs"

    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout

    async def fetch_board_jobs(self, board_token: str, client: Optional[httpx.AsyncClient] = None) -> List[Dict[str, Any]]:
        """
        Fetches live jobs for a given company board token from Greenhouse public API.
        """
        url = self.BASE_URL.format(board_token=board_token)
        close_client = False
        if client is None:
            client = httpx.AsyncClient(timeout=self.timeout)
            close_client = True

        try:
            resp = await client.get(url)
            if resp.status_code == 404:
                logger.info(f"Greenhouse board '{board_token}' not found (404).")
                return []
            resp.raise_for_status()
            data = resp.json()
            return data.get("jobs", [])
        except httpx.HTTPStatusError as e:
            logger.warning(f"Greenhouse HTTP error for board {board_token}: {e}")
            return []
        except Exception as e:
            logger.warning(f"Failed to fetch Greenhouse board {board_token}: {e}")
            return []
        finally:
            if close_client:
                await client.aclose()

    async def fetch_job_detail(self, board_token: str, job_id: str) -> Optional[Dict[str, Any]]:
        url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs/{job_id}"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                resp = await client.get(url)
                if resp.status_code == 200:
                    return resp.json()
            except Exception:
                pass
        return None

    async def search_jobs(
        self,
        keywords: List[str],
        location: Optional[str] = None,
        skills: Optional[List[str]] = None,
        limit: int = 10,
        boards: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieves real jobs across public Greenhouse boards and filters by keywords, location, skills.
        """
        target_boards = boards or select_greenhouse_boards(keywords=keywords, skills=skills)
        normalized_results: List[Dict[str, Any]] = []
        search_terms = [k.lower() for k in (keywords or []) + (skills or [])]
        loc_term = location.lower() if location else None

        async with httpx.AsyncClient(timeout=httpx.Timeout(4.0, connect=2.5)) as client:
            board_tasks = [self.fetch_board_jobs(b, client=client) for b in target_boards]
            board_results = await asyncio.gather(*board_tasks, return_exceptions=True)

            for board, raw_jobs in zip(target_boards, board_results):
                if isinstance(raw_jobs, Exception) or not isinstance(raw_jobs, list):
                    continue
                for item in raw_jobs:
                    job_id = str(item.get("id"))
                    title = item.get("title", "")
                    content = item.get("content", "")
                    loc_name = item.get("location", {}).get("name", "") if isinstance(item.get("location"), dict) else str(item.get("location") or "")
                    job_url = item.get("absolute_url", f"https://boards.greenhouse.io/{board}/jobs/{job_id}")

                    # Matching filter
                    title_lower = title.lower()
                    text_blob = f"{title} {loc_name} {content}".lower()
                    
                    # If location requested, check match
                    if loc_term and loc_term not in text_blob and "remote" not in text_blob:
                        continue

                    # If keywords requested, check if at least one matches
                    is_title_match = False
                    if search_terms:
                        matches_keyword = any(term in text_blob for term in search_terms)
                        if not matches_keyword:
                            continue
                        is_title_match = any(term in title_lower for term in search_terms)

                    normalized = {
                        "provider": "greenhouse",
                        "external_id": f"gh_{board}_{job_id}",
                        "company": board.capitalize(),
                        "title": title,
                        "location": loc_name or "Remote / Unspecified",
                        "description": content[:4000] if content else title,
                        "salary": None,
                        "job_type": "Full-time",
                        "url": job_url,
                        "retrieved_at": datetime.now(timezone.utc),
                        "raw_data": {"board": board, "raw_id": job_id},
                        "_is_title_match": is_title_match
                    }
                    normalized_results.append(normalized)

            # Prioritize jobs matching search terms in the title
            normalized_results.sort(key=lambda x: not x.get("_is_title_match", False))
            for item in normalized_results:
                item.pop("_is_title_match", None)

            return normalized_results[:limit]

        return normalized_results
