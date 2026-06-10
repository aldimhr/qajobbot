import logging
from bs4 import BeautifulSoup
from scrapers.base import BaseScraper
from constants import QA_SEARCH_QUERIES

logger = logging.getLogger(__name__)


class LinkedInScraper(BaseScraper):
    SOURCE = "linkedin"
    API_TEMPLATE = (
        "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
        "?keywords={query}&location=Indonesia&start={start}"
    )

    async def scrape(self) -> list[dict]:
        all_jobs = []
        seen_ids = set()
        for query in QA_SEARCH_QUERIES:
            try:
                for page in range(2):  # 2 pages × 10 = ~20 per query
                    url = self.API_TEMPLATE.format(
                        query=query.replace(" ", "+"), start=page * 10
                    )
                    resp = await self.get(url)
                    soup = BeautifulSoup(resp.text, "lxml")
                    cards = soup.select("div.base-search-card")

                    if not cards:
                        break

                    for card in cards:
                        ext_id = card.get("data-entity-urn", "")
                        if not ext_id or ext_id in seen_ids:
                            continue
                        seen_ids.add(ext_id)

                        title_el = card.select_one("h3.base-search-card__title")
                        company_el = card.select_one("h4.base-search-card__subtitle")
                        loc_el = card.select_one("span.job-search-card__location")
                        link_el = card.select_one("a.base-card__full-link")
                        date_el = card.select_one("time")

                        all_jobs.append({
                            "external_id": ext_id,
                            "source": self.SOURCE,
                            "source_url": link_el["href"].split("?")[0] if link_el else "",
                            "title": title_el.text.strip() if title_el else "",
                            "company_name": company_el.text.strip() if company_el else "",
                            "location": loc_el.text.strip() if loc_el else "Indonesia",
                            "posted_at": date_el.get("datetime", "") if date_el else "",
                        })
            except Exception as e:
                logger.error(f"[{self.SOURCE}] error for query '{query}': {e}")
        logger.info(f"[{self.SOURCE}] scraped {len(all_jobs)} jobs")
        return all_jobs
