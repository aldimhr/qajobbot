import logging
from scrapers.base import BaseScraper
from constants import QA_SEARCH_QUERIES

logger = logging.getLogger(__name__)


class JobStreetScraper(BaseScraper):
    SOURCE = "jobstreet"
    API_URL = (
        "https://id.jobstreet.com/api/jobsearch/v5/jobs?"
        "where=Indonesia&keywords={query}&dateRange=1&pageSize=20&pageNum=1"
    )

    async def scrape(self) -> list[dict]:
        all_jobs = []
        seen_ids = set()
        for query in QA_SEARCH_QUERIES[:4]:
            try:
                url = self.API_URL.format(query=query.replace(" ", "+"))
                resp = await self.get(url, headers={"Accept": "application/json"})
                data = resp.json()
                for job in data.get("results", []):
                    jid = str(job.get("jobId", ""))
                    if jid in seen_ids:
                        continue
                    seen_ids.add(jid)
                    loc = job.get("location", {}) if isinstance(job.get("location"), dict) else {}
                    all_jobs.append({
                        "external_id": jid,
                        "source": self.SOURCE,
                        "source_url": f"https://id.jobstreet.com/job/{jid}",
                        "title": job.get("jobTitle", ""),
                        "company_name": job.get("companyName", ""),
                        "location": loc.get("label", job.get("jobLocation", "")),
                        "work_type": job.get("workType", ""),
                        "posted_at": job.get("listingDate", ""),
                    })
            except Exception as e:
                logger.error(f"[{self.SOURCE}] error for '{query}': {e}")
        logger.info(f"[{self.SOURCE}] scraped {len(all_jobs)} jobs")
        return all_jobs
