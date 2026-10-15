"""
Per-domain rate limiting and Crawl-delay compliance engine.
Ensures responsible crawl intervals matching source registry policies.
"""
import asyncio
import logging
import time

logger = logging.getLogger("financial_watch.compliance.rate_limiter")

class DomainRateLimiter:
    """
    Tracks and enforces timestamps between consecutive requests to the same domain.
    """
    def __init__(self, default_interval_seconds: float = 5.0):
        self.default_interval = max(5.0, default_interval_seconds)
        self._last_access: dict[str, float] = {}
        self._custom_intervals: dict[str, float] = {}
        self._lock = asyncio.Lock()

    def set_domain_interval(self, domain: str, interval_seconds: float):
        """Configure explicit interval with mandatory 5.0s minimum floor (max(5s, crawl_delay))."""
        self._custom_intervals[domain] = max(5.0, interval_seconds)

    async def wait_for_domain(self, domain: str):
        """
        Sleeps if necessary to guarantee the minimum required gap since the last request.
        """
        interval = self._custom_intervals.get(domain, self.default_interval)
        
        async with self._lock:
            now = time.time()
            last_time = self._last_access.get(domain, 0.0)
            elapsed = now - last_time
            
            if elapsed < interval:
                wait_time = interval - elapsed
                logger.info(f"Rate limiter: waiting {wait_time:.2f}s before accessing {domain} (required: {interval}s)")
                await asyncio.sleep(wait_time)
                self._last_access[domain] = time.time()
            else:
                self._last_access[domain] = now
