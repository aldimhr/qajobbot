import logging
from scrapers.base import BaseScraper
from constants import QA_SEARCH_QUERIES

logger = logging.getLogger(__name__)

ENDPOINT = "https://glints.com/api/graphql"

QUERY = """
query Jobs($keyword: String, $page: Int) {
  searchJobs(keyword: $keyword, locationName: "Indonesia", pageNumber: $page, pageSize: 20) {
    jobResult {
      jobs {
        id title createdAt workArrangementOption
        salary { minAmount maxAmount currencyCode }
        location { cityName countryCode }
        company { name }
        descriptionHtml
        skills { name }
        minYearsOfExperience maxYearsOfExperience
      }
    }
  }
}
"""


class GlintsScraper(BaseScraper):
    SOURCE = "glints"

    async def scrape(self) -> list[dict]:
        all_jobs = []
        seen_ids = set()
        for keyword in QA_SEARCH_QUERIES:
            try:
                resp = await self.post(
                    ENDPOINT,
                    json={"query": QUERY, "variables": {"keyword": keyword, "page": 1}},
                    headers={"Content-Type": "application/json"},
                )
                data = resp.json()
                jobs_data = (
                    data.get("data", {})
                    .get("searchJobs", {})
                    .get("jobResult", {})
                    .get("jobs", [])
                )
                for job in jobs_data:
                    jid = str(job.get("id", ""))
                    if jid in seen_ids:
                        continue
                    seen_ids.add(jid)
                    salary = job.get("salary") or {}
                    location = job.get("location") or {}
                    company = job.get("company") or {}
                    all_jobs.append({
                        "external_id": jid,
                        "source": self.SOURCE,
                        "source_url": f"https://glints.com/id/opportunities/jobs/{jid}",
                        "title": job.get("title", ""),
                        "company_name": company.get("name", ""),
                        "location": location.get("cityName", "Indonesia"),
                        "is_remote": job.get("workArrangementOption") == "REMOTE",
                        "salary_min": salary.get("minAmount"),
                        "salary_max": salary.get("maxAmount"),
                        "skills": [s["name"] for s in job.get("skills", [])],
                        "posted_at": job.get("createdAt", ""),
                        "description_raw": job.get("descriptionHtml", ""),
                    })
            except Exception as e:
                logger.error(f"[{self.SOURCE}] error for '{keyword}': {e}")
        logger.info(f"[{self.SOURCE}] scraped {len(all_jobs)} jobs")
        return all_jobs
