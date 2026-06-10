import logging
import feedparser
from scrapers.base import BaseScraper
from constants import QA_SEARCH_QUERIES

logger = logging.getLogger(__name__)


class LinkedInScraper(BaseScraper):
    SOURCE = "linkedin"
    RSS_TEMPLATE = "https://www.linkedin.com/jobs/search/?keywords={query}&location=Indonesia&f_TPR=r86400&format=rss"

    async def scrape(self) -> list[dict]:
        all_jobs = []
        seen_ids = set()
        for query in QA_SEARCH_QUERIES:
            try:
                url = self.RSS_TEMPLATE.format(query=query.replace(" ", "+"))
                resp = await self.get(url)
                feed = feedparser.parse(resp.text)
                for entry in feed.entries:
                    ext_id = entry.get("urn", entry.get("link", ""))
                    if ext_id in seen_ids:
                        continue
                    seen_ids.add(ext_id)
                    company = ""
                    if hasattr(entry, "source") and isinstance(entry.source, dict):
                        company = entry.source.get("title", "")
                    all_jobs.append({
                        "external_id": ext_id,
                        "source": self.SOURCE,
                        "source_url": entry.get("link", ""),
                        "title": entry.get("title", ""),
                        "company_name": company,
                        "location": entry.get("location", "Indonesia"),
                        "posted_at": entry.get("published", ""),
                        "description_raw": entry.get("summary", ""),
                    })
            except Exception as e:
                logger.error(f"[{self.SOURCE}] error for query '{query}': {e}")
        logger.info(f"[{self.SOURCE}] scraped {len(all_jobs)} jobs")
        return all_jobs
