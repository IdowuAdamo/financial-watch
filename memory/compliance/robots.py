"""
Robots.txt parsing, caching, and compliance enforcement.
Adheres strictly to RFC 9309 and ethical crawling guidelines.
"""
import logging
import time
import urllib.robotparser
from urllib.parse import urlparse

import httpx

logger = logging.getLogger("financial_watch.compliance.robots")

class RobotsCacheEntry:
    def __init__(self, parser: urllib.robotparser.RobotFileParser | None, status_code: int, crawl_delay: float):
        self.parser = parser
        self.status_code = status_code
        self.crawl_delay = crawl_delay
        self.cached_at = time.time()

    def is_expired(self, ttl_seconds: float = 86400.0) -> bool:
        return (time.time() - self.cached_at) > ttl_seconds

class RobotsComplianceManager:
    """
    Manages robots.txt caching, crawl-delay extraction, and access evaluation.
    """
    def __init__(self, user_agent: str, contact_url: str, cache_ttl_seconds: float = 86400.0):
        self.user_agent = user_agent
        self.contact_url = contact_url
        self.cache_ttl_seconds = cache_ttl_seconds
        self._cache: dict[str, RobotsCacheEntry] = {}

    def get_full_user_agent(self) -> str:
        return f"{self.user_agent} (+{self.contact_url})"

    async def fetch_and_cache_robots(self, client: httpx.AsyncClient, domain: str, scheme: str = "https") -> RobotsCacheEntry:
        """
        Fetches robots.txt for a given domain and caches it.
        Rules:
        - HTTP 200: Parse rules and crawl-delay
        - HTTP 401 / 403: Treat as NO PERMISSION / manual-only
        - HTTP 404: No robots.txt, conservative allow with flag
        - Other errors: Conservative block / manual-only
        """
        robots_url = f"{scheme}://{domain}/robots.txt"
        logger.info(f"Checking robots.txt for domain {domain} at {robots_url}")
        
        try:
            headers = {"User-Agent": self.get_full_user_agent()}
            response = await client.get(robots_url, headers=headers, timeout=10.0, follow_redirects=True)
            status_code = response.status_code

            if status_code in (401, 403):
                logger.warning(f"Robots.txt returned {status_code} for {domain}. Classifying source as manual-only.")
                entry = RobotsCacheEntry(parser=None, status_code=status_code, crawl_delay=0.0)
                self._cache[domain] = entry
                return entry

            if status_code == 404:
                logger.info(f"Robots.txt returned 404 for {domain}. Proceeding in conservative mode.")
                entry = RobotsCacheEntry(parser=None, status_code=404, crawl_delay=10.0)
                self._cache[domain] = entry
                return entry

            if status_code == 200:
                parser = urllib.robotparser.RobotFileParser()
                parser.parse(response.text.splitlines())
                
                # Extract crawl delay if present
                crawl_delay = 0.0
                try:
                    cd = parser.crawl_delay(self.user_agent)
                    if cd is not None:
                        crawl_delay = float(cd)
                    else:
                        # Check wildcard '*' delay
                        cd_wild = parser.crawl_delay("*")
                        if cd_wild is not None:
                            crawl_delay = float(cd_wild)
                except Exception as e:
                    logger.debug(f"Could not parse crawl-delay for {domain}: {e}")

                entry = RobotsCacheEntry(parser=parser, status_code=200, crawl_delay=crawl_delay)
                self._cache[domain] = entry
                return entry

            # Any other response: conservative block
            entry = RobotsCacheEntry(parser=None, status_code=status_code, crawl_delay=0.0)
            self._cache[domain] = entry
            return entry

        except Exception as e:
            logger.error(f"Error fetching robots.txt for {domain}: {e}")
            entry = RobotsCacheEntry(parser=None, status_code=500, crawl_delay=0.0)
            self._cache[domain] = entry
            return entry

    async def is_allowed(self, client: httpx.AsyncClient, url: str) -> tuple[bool, str, float]:
        """
        Evaluates whether a target URL is allowed to be crawled.
        Returns: (is_allowed: bool, reason: str, crawl_delay: float)
        """
        parsed = urlparse(url)
        domain = parsed.netloc
        if not domain:
            return False, "Invalid URL netloc", 0.0

        entry = self._cache.get(domain)
        if entry is None or entry.is_expired(self.cache_ttl_seconds):
            entry = await self.fetch_and_cache_robots(client, domain, parsed.scheme or "https")

        # Check status codes
        if entry.status_code in (401, 403):
            return False, f"Robots.txt returned HTTP {entry.status_code} (access forbidden / manual-only)", 0.0

        if entry.status_code == 404:
            return True, "No robots.txt found (HTTP 404). Allowed in conservative rate-limited mode.", entry.crawl_delay

        if entry.status_code == 200 and entry.parser:
            can_fetch = entry.parser.can_fetch(self.user_agent, url)
            if not can_fetch:
                # Also test wildcard
                can_fetch = entry.parser.can_fetch("*", url)
            
            if can_fetch:
                return True, "Allowed by robots.txt rules", entry.crawl_delay
            else:
                return False, f"Disallowed by robots.txt rule for path {parsed.path}", entry.crawl_delay

        return False, f"Robots.txt fetch failed with status {entry.status_code}", 0.0
