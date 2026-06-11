"""LinkedIn Posts scraper — finds QA job announcements from user/company feed posts.

Uses Brave Search (site:linkedin.com/posts) since LinkedIn's content search
requires login and Google/Bing CAPTCHA our server IP.
"""

import re
import random
import logging
import hashlib
from scrapers.base import BaseScraper
from enrichment.post_parser import (
    is_qa_post, extract_job_title, extract_company,
    extract_location, extract_apply_url, extract_description,
)
from constants import LINKEDIN_POST_QUERIES, USER_AGENTS

logger = logging.getLogger(__name__)

# Brave search queries targeting LinkedIn posts
BRAVE_QUERIES = [
    'site:linkedin.com/posts "qa engineer" hiring indonesia',
    'site:linkedin.com/posts "tester" hiring indonesia',
    'site:linkedin.com/posts "quality assurance" hiring',
    'site:linkedin.com/posts "qa automation" hiring',
    'site:linkedin.com/posts "selenium" hiring',
    'site:linkedin.com/posts "test engineer" hiring',
    'site:linkedin.com/posts lowongan "qa"',
    'site:linkedin.com/posts lowongan "tester"',
    'site:linkedin.com/posts dicari "qa engineer"',
    'site:linkedin.com/posts mencari "qa"',
]


class LinkedInPostsScraper(BaseScraper):
    """Scrapes LinkedIn posts via Brave Search for QA job announcements."""

    SOURCE = "linkedin_posts"

    async def scrape(self) -> list[dict]:
        """Search Brave for LinkedIn posts about QA jobs."""
        all_jobs = []
        seen_ids = set()

        # Pick 4 random queries per run to rotate
        queries = random.sample(BRAVE_QUERIES, min(4, len(BRAVE_QUERIES)))

        for query in queries:
            try:
                posts = await self._brave_search(query, seen_ids)
                logger.info(f"[{self.SOURCE}] query '{query}': found {len(posts)} posts")

                for post in posts:
                    text = post.get("text", "")

                    # Filter: must be QA-related with hiring signals
                    if not is_qa_post(text):
                        continue

                    title = extract_job_title(text)
                    company = extract_company(text, post.get("author", ""))
                    location = extract_location(text)
                    apply_url = extract_apply_url(text) or post.get("url", "")
                    desc = extract_description(text)

                    is_remote = bool(re.search(
                        r"\b(remote|wfh|work from home|work from anywhere)\b",
                        text, re.IGNORECASE
                    ))

                    job = {
                        "external_id": post.get("id", ""),
                        "source": self.SOURCE,
                        "source_url": post.get("url", ""),
                        "title": title,
                        "company_name": company,
                        "location": location or "Indonesia",
                        "is_remote": is_remote,
                        "description_raw": desc,
                        "posted_at": post.get("posted_at", ""),
                    }
                    all_jobs.append(job)

            except Exception as e:
                logger.error(f"[{self.SOURCE}] error for query '{query}': {e}")

        logger.info(f"[{self.SOURCE}] scraped {len(all_jobs)} QA job posts")
        return all_jobs

    async def _brave_search(self, query: str, seen_ids: set) -> list[dict]:
        """Search Brave and parse LinkedIn post results."""
        from bs4 import BeautifulSoup

        url = f"https://search.brave.com/search?q={query.replace(' ', '+')}"

        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "id-ID,id;q=0.9,en;q=0.8",
            "User-Agent": random.choice(USER_AGENTS),
        }
        self.client.headers.update(headers)

        try:
            resp = await self.get(url)
        except Exception as e:
            logger.warning(f"[{self.SOURCE}] Brave search failed: {e}")
            return []

        if resp.status_code != 200:
            logger.warning(f"[{self.SOURCE}] Brave returned {resp.status_code}")
            return []

        soup = BeautifulSoup(resp.text, "lxml")
        posts = []

        # Parse Brave search results
        # Brave uses .snippet class for search results
        results = soup.select("div.snippet, div.data-result")

        # Also try generic result selectors
        if not results:
            results = soup.select("div[class*='result']")

        for result in results:
            try:
                # Find LinkedIn post links
                link_el = result.select_one("a[href*='linkedin.com/posts/']") or \
                          result.select_one("a[href*='linkedin.com/pulse/']")

                if not link_el:
                    # Check all links in this result
                    for a in result.select("a[href]"):
                        href = a.get("href", "")
                        if "linkedin.com/posts/" in href:
                            link_el = a
                            break

                if not link_el:
                    continue

                href = link_el["href"]
                if "linkedin.com" not in href:
                    continue

                # Extract title/snippet
                title_el = result.select_one("div.snippet-title, h3, .title")
                snippet_el = result.select_one("div.snippet-description, p, .description")

                title_text = title_el.get_text(strip=True) if title_el else ""
                snippet_text = snippet_el.get_text(strip=True) if snippet_el else ""

                # Combine title + snippet as post text
                full_text = f"{title_text} {snippet_text}".strip()

                if not full_text:
                    continue

                # Generate unique ID from URL
                clean_url = href.split("?")[0]
                post_id = hashlib.md5(clean_url.encode()).hexdigest()[:16]
                if post_id in seen_ids:
                    continue
                seen_ids.add(post_id)

                # Extract author from title (usually "Author on LinkedIn: post text")
                author = ""
                if " on LinkedIn:" in title_text:
                    author = title_text.split(" on LinkedIn:")[0].strip()
                elif " di LinkedIn:" in title_text:
                    author = title_text.split(" di LinkedIn:")[0].strip()
                elif "LinkedIn" in title_text:
                    # Try to extract author before "LinkedIn"
                    parts = title_text.split("LinkedIn")
                    if parts[0].strip():
                        author = parts[0].strip().rstrip(" -–—")

                # Get the actual post text (after "LinkedIn:" in title)
                post_text = title_text
                if "LinkedIn:" in title_text:
                    post_text = title_text.split("LinkedIn:", 1)[1].strip()
                elif "LinkedIn" in title_text:
                    # Remove "LinkedIn" prefix and common separators
                    post_text = re.sub(r"^.*?LinkedIn\s*[-–—:]*\s*", "", title_text).strip()

                # Combine with snippet for more context
                if snippet_text and snippet_text not in post_text:
                    post_text = f"{post_text} {snippet_text}"

                posts.append({
                    "id": post_id,
                    "author": author,
                    "text": post_text,
                    "url": clean_url,
                    "posted_at": "",
                })

            except Exception as e:
                logger.debug(f"[{self.SOURCE}] error parsing Brave result: {e}")
                continue

        return posts
