import logging
import json
from scrapers.pw_base import PlaywrightBaseScraper
from proxy_pool import proxy_pool
from constants import QA_SEARCH_QUERIES

logger = logging.getLogger(__name__)


class JobStreetScraper(PlaywrightBaseScraper):
    SOURCE = "jobstreet"
    URL_TEMPLATE = (
        "https://www.jobstreet.co.id/jobs?keywords={query}&sortmode=ListedDate"
    )

    async def scrape(self) -> list[dict]:
        all_jobs = []
        seen_ids = set()

        proxy = proxy_pool.get()
        if not proxy:
            logger.warning(f"[{self.SOURCE}] No proxies available, skipping")
            return []

        try:
            await self._launch_browser()
            for query in QA_SEARCH_QUERIES[:4]:  # Top 4 to avoid too many requests
                try:
                    url = self.URL_TEMPLATE.format(query=query.replace(" ", "+"))
                    page = await self._browser.new_page(
                        proxy={"server": f"http://{proxy}"},
                        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                        locale="id-ID",
                    )
                    await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                    await page.wait_for_timeout(5000)  # Wait for Cloudflare challenge

                    # Check if still on Cloudflare challenge
                    body_text = await page.evaluate("document.body.innerText")
                    if "security verification" in body_text.lower() or "captcha" in body_text.lower():
                        logger.warning(f"[{self.SOURCE}] Cloudflare challenge for '{query}', proxy {proxy}")
                        await page.close()
                        proxy = proxy_pool.get() or proxy
                        continue

                    # Try to find __NEXT_DATA__ first
                    next_data = await page.evaluate("""
                        () => {
                            const el = document.getElementById('__NEXT_DATA__');
                            return el ? el.textContent : null;
                        }
                    """)

                    if next_data:
                        data = json.loads(next_data)
                        results = (
                            data.get("props", {})
                            .get("pageProps", {})
                            .get("results", [])
                        )
                        for job in results:
                            jid = str(job.get("id", job.get("jobId", "")))
                            if not jid or jid in seen_ids:
                                continue
                            seen_ids.add(jid)
                            company = job.get("company", {})
                            location = job.get("location", {})
                            all_jobs.append({
                                "external_id": jid,
                                "source": self.SOURCE,
                                "source_url": f"https://www.jobstreet.co.id/job/{jid}",
                                "title": job.get("title", job.get("jobTitle", "")),
                                "company_name": company.get("name", "") if isinstance(company, dict) else job.get("companyName", ""),
                                "location": location.get("label", "") if isinstance(location, dict) else str(location),
                                "posted_at": job.get("listingDate", ""),
                            })
                    else:
                        # Fallback: scrape HTML job links
                        links = await page.query_selector_all('a[data-automation="jobTitle"]')
                        if not links:
                            links = await page.query_selector_all('a[href*="/job/"]')

                        for link in links:
                            href = await link.get_attribute("href") or ""
                            title = (await link.inner_text()).strip()
                            if not title or not href:
                                continue

                            # Extract job ID from URL
                            parts = href.rstrip("/").split("/")
                            jid = parts[-1] if parts else ""
                            if not jid or jid in seen_ids:
                                continue
                            seen_ids.add(jid)

                            full_url = href if href.startswith("http") else f"https://www.jobstreet.co.id{href}"
                            all_jobs.append({
                                "external_id": jid,
                                "source": self.SOURCE,
                                "source_url": full_url,
                                "title": title,
                                "company_name": "",
                                "location": "Indonesia",
                            })

                    await page.close()
                except Exception as e:
                    logger.error(f"[{self.SOURCE}] error for '{query}': {e}")
                    try:
                        await page.close()
                    except Exception:
                        pass
        except Exception as e:
            logger.error(f"[{self.SOURCE}] browser error: {e}")
        finally:
            await self._close_browser()

        logger.info(f"[{self.SOURCE}] scraped {len(all_jobs)} jobs")
        return all_jobs
