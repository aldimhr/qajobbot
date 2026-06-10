import httpx
import random
import asyncio
import logging
from constants import USER_AGENTS

logger = logging.getLogger(__name__)


class BaseScraper:
    """Base class for all job scrapers with rate limiting and UA rotation."""

    SOURCE: str = "unknown"

    def __init__(self, proxy_url: str = ""):
        headers = {
            "Accept-Language": "id-ID,id;q=0.9,en;q=0.8",
            "Accept": "text/html,application/xhtml+xml,application/json",
        }
        kwargs = {"timeout": 20, "headers": headers, "follow_redirects": True}
        if proxy_url:
            kwargs["proxy"] = proxy_url
        self.client = httpx.AsyncClient(**kwargs)
        self._last_request: dict[str, float] = {}

    async def get(self, url: str, **kwargs) -> httpx.Response:
        domain = httpx.URL(url).host
        elapsed = asyncio.get_event_loop().time() - self._last_request.get(domain, 0)
        if elapsed < 3:
            await asyncio.sleep(3 - elapsed + random.uniform(0, 2))

        self.client.headers["User-Agent"] = random.choice(USER_AGENTS)
        try:
            resp = await self.client.get(url, **kwargs)
            resp.raise_for_status()
            self._last_request[domain] = asyncio.get_event_loop().time()
            return resp
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                logger.warning(f"[{self.SOURCE}] Rate limited, backing off 60s")
                await asyncio.sleep(60)
            raise

    async def post(self, url: str, **kwargs) -> httpx.Response:
        domain = httpx.URL(url).host
        elapsed = asyncio.get_event_loop().time() - self._last_request.get(domain, 0)
        if elapsed < 3:
            await asyncio.sleep(3 - elapsed + random.uniform(0, 2))

        self.client.headers["User-Agent"] = random.choice(USER_AGENTS)
        resp = await self.client.post(url, **kwargs)
        resp.raise_for_status()
        self._last_request[domain] = asyncio.get_event_loop().time()
        return resp

    async def scrape(self) -> list[dict]:
        """Override in subclasses. Returns list of raw job dicts."""
        raise NotImplementedError

    async def close(self):
        await self.client.aclose()
