import logging
from scrapers.base import BaseScraper
from constants import QA_SEARCH_QUERIES

logger = logging.getLogger(__name__)


class KalibrrScraper(BaseScraper):
    SOURCE = "kalibrr"
    API_URL = "https://www.kalibrr.com/api/jobs?search={query}&location=Indonesia&sort=date&limit=20&offset=0"

    async def scrape(self) -> list[dict]:
        all_jobs = []
        seen_ids = set()
        for query in QA_SEARCH_QUERIES[:4]:
            try:
                url = self.API_URL.format(query=query.replace(" ", "+"))
                resp = await self.get(url)
                data = resp.json()
                for job in data.get("data", []):
                    jid = str(job.get("id", ""))
                    if jid in seen_ids:
                        continue
                    seen_ids.add(jid)
                    company = job.get("company", {})
                    location = job.get("location", {})
                    all_jobs.append({
                        "external_id": jid,
                        "source": self.SOURCE,
                        "source_url": f"https://www.kalibrr.com/job/{jid}",
                        "title": job.get("title", ""),
                        "company_name": company.get("name", "") if isinstance(company, dict) else str(company),
                        "location": location.get("name", "") if isinstance(location, dict) else str(location),
                        "work_type": job.get("job_type", ""),
                        "salary_min": job.get("min_salary"),
                        "salary_max": job.get("max_salary"),
                        "posted_at": job.get("published_at", ""),
                        "description_raw": job.get("description", ""),
                    })
            except Exception as e:
                logger.error(f"[{self.SOURCE}] error for '{query}': {e}")
        logger.info(f"[{self.SOURCE}] scraped {len(all_jobs)} jobs")
        return all_jobs
