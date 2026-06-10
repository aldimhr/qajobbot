import logging
import json
import httpx
from bs4 import BeautifulSoup
from scrapers.base import BaseScraper
from proxy_pool import proxy_pool
from constants import QA_SEARCH_QUERIES

logger = logging.getLogger(__name__)


class GlintsScraper(BaseScraper):
    SOURCE = "glints"
    URL_TEMPLATE = (
        "https://glints.com/id/opportunities/jobs/explore"
        "?keyword={query}&country=ID&sortBy=LATEST"
    )

    async def scrape(self) -> list[dict]:
        all_jobs = []
        seen_ids = set()

        proxy = proxy_pool.get()
        if not proxy:
            logger.warning(f"[{self.SOURCE}] No proxies available, skipping")
            return []

        # Override client with proxy
        self.client = httpx.AsyncClient(
            timeout=20,
            proxy=f"http://{proxy}",
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                "Accept-Language": "id-ID,id;q=0.9,en;q=0.8",
                "Accept": "text/html,application/xhtml+xml,application/json",
            },
        )

        for query in QA_SEARCH_QUERIES:
            try:
                url = self.URL_TEMPLATE.format(query=query.replace(" ", "+"))
                resp = await self.get(url)
                soup = BeautifulSoup(resp.text, "lxml")

                script = soup.select_one("script#__NEXT_DATA__")
                if not script or not script.string:
                    logger.warning(f"[{self.SOURCE}] No __NEXT_DATA__ for '{query}'")
                    continue

                data = json.loads(script.string)
                jobs_data = (
                    data.get("props", {})
                    .get("pageProps", {})
                    .get("initialJobs", {})
                    .get("jobsInPage", [])
                )

                for job in jobs_data:
                    jid = str(job.get("id", ""))
                    if not jid or jid in seen_ids:
                        continue
                    seen_ids.add(jid)

                    company = job.get("company") or {}
                    city = job.get("city") or {}
                    location = job.get("location") or {}
                    salaries = job.get("salaries") or []
                    raw_skills = job.get("skills") or []

                    # Extract salary
                    salary_min = None
                    salary_max = None
                    if salaries:
                        s = salaries[0]
                        salary_min = s.get("minAmount")
                        salary_max = s.get("maxAmount")

                    # Extract skills (filter empty)
                    skills = [s.get("name", "") for s in raw_skills if s.get("name")]

                    # Location: prefer city, fallback to location, fallback to country
                    loc_str = (
                        city.get("name")
                        or location.get("formattedName")
                        or location.get("name")
                        or (job.get("country") or {}).get("name", "Indonesia")
                    )

                    all_jobs.append({
                        "external_id": jid,
                        "source": self.SOURCE,
                        "source_url": f"https://glints.com/id/opportunities/jobs/opportunity/{jid}",
                        "title": job.get("title", ""),
                        "company_name": company.get("name", ""),
                        "location": loc_str,
                        "is_remote": (job.get("workArrangementOption") or "").upper() == "REMOTE",
                        "salary_min": salary_min,
                        "salary_max": salary_max,
                        "skills": skills,
                        "posted_at": job.get("createdAt", ""),
                    })

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 403:
                    logger.warning(f"[{self.SOURCE}] Blocked for '{query}', rotating proxy")
                    new_proxy = proxy_pool.get()
                    if new_proxy and new_proxy != proxy:
                        proxy = new_proxy
                        self.client = httpx.AsyncClient(
                            timeout=20,
                            proxy=f"http://{proxy}",
                            follow_redirects=True,
                            headers=dict(self.client.headers),
                        )
                else:
                    logger.error(f"[{self.SOURCE}] HTTP {e.response.status_code} for '{query}'")
            except Exception as e:
                logger.error(f"[{self.SOURCE}] error for '{query}': {e}")

        logger.info(f"[{self.SOURCE}] scraped {len(all_jobs)} jobs")
        return all_jobs
