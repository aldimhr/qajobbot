import logging
from scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


class RemotiveScraper(BaseScraper):
    SOURCE = "remotive"
    API_URL = "https://remotive.com/api/remote-jobs?category=qa&limit=50"

    async def scrape(self) -> list[dict]:
        try:
            resp = await self.get(self.API_URL)
            data = resp.json()
            jobs = []
            for item in data.get("jobs", []):
                jobs.append({
                    "external_id": str(item.get("id", "")),
                    "source": self.SOURCE,
                    "source_url": item.get("url", ""),
                    "title": item.get("title", ""),
                    "company_name": item.get("company_name", ""),
                    "location": item.get("candidate_required_location", "Remote"),
                    "is_remote": True,
                    "salary_min": None,
                    "salary_max": None,
                    "description_summary": (item.get("description", "") or "")[:200],
                    "skills": item.get("tags", []),
                    "posted_at": item.get("publication_date", ""),
                })
            logger.info(f"[{self.SOURCE}] scraped {len(jobs)} jobs")
            return jobs
        except Exception as e:
            logger.error(f"[{self.SOURCE}] scrape error: {e}")
        return []
