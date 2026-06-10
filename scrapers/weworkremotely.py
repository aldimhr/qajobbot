import logging
import feedparser
from scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


class WWRScraper(BaseScraper):
    SOURCE = "weworkremotely"
    RSS_URL = "https://weworkremotely.com/remote-jobs.rss"

    async def scrape(self) -> list[dict]:
        try:
            resp = await self.get(self.RSS_URL)
            feed = feedparser.parse(resp.text)
            jobs = []
            for entry in feed.entries:
                jobs.append({
                    "external_id": entry.get("id", entry.get("link", "")),
                    "source": self.SOURCE,
                    "source_url": entry.get("link", ""),
                    "title": entry.get("title", ""),
                    "company_name": entry.get("author", ""),
                    "location": "Remote",
                    "is_remote": True,
                    "description_summary": (entry.get("summary", "") or "")[:200],
                    "posted_at": entry.get("published", ""),
                })
            logger.info(f"[{self.SOURCE}] scraped {len(jobs)} jobs")
            return jobs
        except Exception as e:
            logger.error(f"[{self.SOURCE}] scrape error: {e}")
        return []
