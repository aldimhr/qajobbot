"""Proxy pool manager — fetches free proxies, tests them, rotates."""
import asyncio
import random
import logging
import httpx

logger = logging.getLogger(__name__)

PROXY_SOURCES = [
    "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=5000&country=all&ssl=yes&anonymity=all",
]


class ProxyPool:
    def __init__(self):
        self._proxies: list[str] = []
        self._tested: list[str] = []
        self._lock = asyncio.Lock()

    async def refresh(self):
        """Fetch and test proxies."""
        all_proxies = set()
        async with httpx.AsyncClient(timeout=10) as c:
            for url in PROXY_SOURCES:
                try:
                    r = await c.get(url)
                    for line in r.text.strip().split("\n"):
                        p = line.strip()
                        if p and ":" in p:
                            all_proxies.add(p)
                except Exception:
                    pass

        logger.info(f"[proxy] Fetched {len(all_proxies)} candidate proxies, testing...")
        tested = []
        # Test in batches of 5
        proxy_list = list(all_proxies)
        random.shuffle(proxy_list)
        for i in range(0, min(len(proxy_list), 20), 5):
            batch = proxy_list[i : i + 5]
            results = await asyncio.gather(
                *[self._test(p) for p in batch], return_exceptions=True
            )
            for proxy, result in zip(batch, results):
                if result is True:
                    tested.append(proxy)

        async with self._lock:
            self._proxies = tested
            self._tested = tested

        logger.info(f"[proxy] {len(tested)} working proxies in pool")

    async def _test(self, proxy: str) -> bool:
        try:
            async with httpx.AsyncClient(
                timeout=5, proxy=f"http://{proxy}", follow_redirects=True
            ) as c:
                r = await c.get("https://httpbin.org/ip")
                return r.status_code == 200
        except Exception:
            return False

    def get(self) -> str | None:
        """Get a random working proxy."""
        if not self._proxies:
            return None
        return random.choice(self._proxies)

    def get_all(self) -> list[str]:
        return list(self._proxies)

    @property
    def count(self) -> int:
        return len(self._proxies)


# Singleton
proxy_pool = ProxyPool()
