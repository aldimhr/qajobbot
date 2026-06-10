import logging
from scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


class RemoteOKScraper(BaseScraper):
    SOURCE = "remoteok"
    API_URL = "https://remoteok.com/api"

    async def scrape(self) -> list[dict]:
        try:
            resp = await self.get(self.API_URL)
            data = resp.json()
            if isinstance(data, list) and len(data) > 1:
                jobs = []
                for item in data[1:]:
                    if not isinstance(item, dict):
                        continue
                    jobs.append({
                        "external_id": str(item.get("id", "")),
                        "source": self.SOURCE,
                        "source_url": item.get("url", f"https://remoteok.com/remote-jobs/{item.get('id', '')}"),
                        "title": item.get("position", ""),
                        "company_name": item.get("company", ""),
                        "location": item.get("location", "Remote"),
                        "is_remote": True,
                        "salary_min": item.get("salary_min"),
                        "salary_max": item.get("salary_max"),
                        "description_summary": (item.get("description", "") or "")[:200],
                        "skills": item.get("tags", []),
                        "posted_at": item.get("date", ""),
                    })
                logger.info(f"[{self.SOURCE}] scraped {len(jobs)} jobs")
                return jobs
        except Exception as e:
            logger.error(f"[{self.SOURCE}] scrape error: {e}")
        return []
