import asyncio
import logging
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)


class PlaywrightBaseScraper:
    """Base scraper using Playwright for JS-rendered pages."""

    SOURCE: str = "unknown"

    async def _launch_browser(self):
        self._pw = await async_playwright().start()
        self._browser = await self._pw.chromium.launch(
            headless=True, args=["--no-sandbox", "--disable-gpu"]
        )

    async def _close_browser(self):
        if hasattr(self, "_browser") and self._browser:
            await self._browser.close()
        if hasattr(self, "_pw") and self._pw:
            await self._pw.stop()

    async def _get_page(self, url: str, wait_seconds: float = 3):
        """Navigate to URL, wait for JS to render, return page."""
        page = await self._browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            locale="id-ID",
        )
        await page.goto(url, wait_until="domcontentloaded", timeout=20000)
        await asyncio.sleep(wait_seconds)
        return page

    async def scrape(self) -> list[dict]:
        """Override in subclasses."""
        raise NotImplementedError

    async def close(self):
        await self._close_browser()
