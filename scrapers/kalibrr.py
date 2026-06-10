import logging
from scrapers.pw_base import PlaywrightBaseScraper

logger = logging.getLogger(__name__)


class KalibrrScraper(PlaywrightBaseScraper):
    SOURCE = "kalibrr"
    HOME_URL = "https://www.kalibrr.com/"

    async def scrape(self) -> list[dict]:
        all_jobs = []
        seen_ids = set()
        try:
            await self._launch_browser()
            page = await self._get_page(self.HOME_URL, wait_seconds=4)

            # Find all job links on the home page
            links = await page.query_selector_all('a[href*="/jobs/"]')
            for link in links:
                href = await link.get_attribute("href")
                if not href or "/jobs/" not in href:
                    continue

                # Extract job ID from URL pattern: /id-ID/c/{company}/jobs/{id}/{slug}
                parts = href.split("/jobs/")
                if len(parts) < 2:
                    continue
                job_id_part = parts[1].split("/")[0]
                if not job_id_part.isdigit():
                    continue

                if job_id_part in seen_ids:
                    continue
                seen_ids.add(job_id_part)

                title = (await link.inner_text()).strip()
                if not title or title.lower() in ("view post", ""):
                    continue

                # Extract company from URL
                company = ""
                if "/c/" in href:
                    company = href.split("/c/")[1].split("/")[0] if "/c/" in href else ""

                # Build full URL
                full_url = href if href.startswith("http") else f"https://www.kalibrr.com{href}"

                all_jobs.append({
                    "external_id": f"kalibrr-{job_id_part}",
                    "source": self.SOURCE,
                    "source_url": full_url,
                    "title": title,
                    "company_name": company.replace("-", " ").title(),
                    "location": "Indonesia",
                })

            await page.close()
            logger.info(f"[{self.SOURCE}] scraped {len(all_jobs)} jobs from home page")
        except Exception as e:
            logger.error(f"[{self.SOURCE}] scrape error: {e}")
        finally:
            await self._close_browser()
        return all_jobs
