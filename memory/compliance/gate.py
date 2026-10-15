"""
Compliance Gate: Unified compliance enforcer for all web document retrieval.
Integrates robots.txt rules, domain rate limits, section allowlists, and audit logs.
"""
import logging
import os
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

import httpx
import yaml

from memory.compliance.rate_limiter import DomainRateLimiter
from memory.compliance.robots import RobotsComplianceManager

logger = logging.getLogger("financial_watch.compliance.gate")

class ComplianceDecisionLog:
    def __init__(self, source_id: str, url: str, decision: str, reason: str, details: dict[str, Any] | None = None):
        self.timestamp = datetime.now(UTC).isoformat()
        self.source_id = source_id
        self.url = url
        self.decision = decision # "ALLOWED" or "DENIED"
        self.reason = reason
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "source_id": self.source_id,
            "url": self.url,
            "decision": self.decision,
            "reason": self.reason,
            "details": self.details,
        }

class ComplianceGate:
    """
    The mandatory compliance gateway through which all external fetches pass.
    """
    def __init__(
        self,
        registry_path: str | None = None,
        contact_url: str | None = None,
        user_agent_name: str = "FinancialWatchBot/1.0"
    ):
        self.contact_url = contact_url or os.getenv(
            "CRAWLER_CONTACT_URL",
            "https://github.com/IdowuAdamo/financial-watch"
        )
        self.user_agent_name = user_agent_name
        self.robots_manager = RobotsComplianceManager(
            user_agent=self.user_agent_name,
            contact_url=self.contact_url
        )
        self.rate_limiter = DomainRateLimiter(default_interval_seconds=5.0)
        self.sources: dict[str, dict[str, Any]] = {}
        self.audit_log: list[ComplianceDecisionLog] = []

        # Load registry (defaulting to standard sources.yaml)
        if not registry_path:
            default_yaml = os.path.join(os.path.dirname(__file__), "..", "registry", "sources.yaml")
            if os.path.exists(default_yaml):
                registry_path = default_yaml

        if registry_path and os.path.exists(registry_path):
            self.load_registry(registry_path)

    def load_registry(self, yaml_path: str):
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            for src in data.get("sources", []):
                self.sources[src["id"]] = src
                # Configure rate limiter from registry with mandatory 5s floor (max(5s, crawl_delay))
                raw_delay = src.get("rate_limit_seconds") or src.get("crawl_delay_seconds") or 5.0
                rate_limit = max(5.0, float(raw_delay))
                if "base_url" in src and not src["base_url"].startswith("internal://"):
                    domain = urlparse(src["base_url"]).netloc
                    if domain:
                        self.rate_limiter.set_domain_interval(domain, rate_limit)

    def get_source_config(self, source_id: str) -> dict[str, Any] | None:
        return self.sources.get(source_id)

    def log_decision(self, source_id: str, url: str, decision: str, reason: str, details: dict[str, Any] | None = None):
        entry = ComplianceDecisionLog(source_id, url, decision, reason, details)
        self.audit_log.append(entry)
        if decision == "ALLOWED":
            logger.info(f"[COMPLIANCE: ALLOWED] {source_id} - {url} ({reason})")
        else:
            logger.warning(f"[COMPLIANCE: DENIED] {source_id} - {url} ({reason})")

    async def check_url_compliance(self, client: httpx.AsyncClient, source_id: str, url: str) -> tuple[bool, str]:
        """
        Runs full compliance checklist:
        1. Check if source is active and not manual-only
        2. Check section allowlist if configured
        3. Check robots.txt status and disallows
        """
        source = self.get_source_config(source_id)
        if not source:
            reason = f"Source ID '{source_id}' not found in registry"
            self.log_decision(source_id, url, "DENIED", reason)
            return False, reason

        # Internal simulated sources are automatically compliant
        if source.get("access_method") == "internal_seed" or url.startswith("internal://"):
            self.log_decision(source_id, url, "ALLOWED", "Internal simulated client source")
            return True, "Internal simulated client source"

        # Check manual-only status
        if source.get("access_method") == "manual_curation_only":
            reason = f"Source '{source['name']}' is classified as manual-only (bot protection / 403). Automated crawling disallowed."
            self.log_decision(source_id, url, "DENIED", reason)
            return False, reason

        parsed = urlparse(url)
        path = parsed.path

        # Check section allowlist if present
        allowlist = source.get("section_allowlist", [])
        if allowlist:
            matched = any(path.startswith(prefix) for prefix in allowlist)
            if not matched:
                reason = f"Path '{path}' is not within approved section allowlist {allowlist}"
                self.log_decision(source_id, url, "DENIED", reason)
                return False, reason

        # Check robots.txt rules
        allowed, robots_reason, crawl_delay = await self.robots_manager.is_allowed(client, url)
        if not allowed:
            self.log_decision(source_id, url, "DENIED", robots_reason, {"crawl_delay": crawl_delay})
            return False, robots_reason

        # If a crawl-delay was detected in robots.txt and exceeds our default, update rate limiter
        if crawl_delay > 0:
            domain = parsed.netloc
            self.rate_limiter.set_domain_interval(domain, crawl_delay)

        self.log_decision(source_id, url, "ALLOWED", f"Passed robots.txt and section allowlist. {robots_reason}")
        return True, "Compliant"

    async def fetch_url(self, client: httpx.AsyncClient, source_id: str, url: str) -> httpx.Response | None:
        """
        Executes a compliant HTTP GET request:
        - Evaluates compliance gate
        - Enforces domain rate limit
        - Sends verified User-Agent with contact URL
        - Gracefully handles 403/429 without aggressive retries
        """
        is_compliant, reason = await self.check_url_compliance(client, source_id, url)
        if not is_compliant:
            logger.warning(f"Aborting fetch for {url}: {reason}")
            return None

        parsed = urlparse(url)
        domain = parsed.netloc

        # Enforce rate limiter sleep
        await self.rate_limiter.wait_for_domain(domain)

        headers = {
            "User-Agent": self.robots_manager.get_full_user_agent(),
            "Accept": "text/html,application/xhtml+xml,application/pdf;q=0.9,*/*;q=0.8",
        }

        try:
            logger.info(f"Fetching compliant resource: {url}")
            response = await client.get(url, headers=headers, timeout=20.0, follow_redirects=True)
            
            if response.status_code in (403, 429):
                logger.warning(f"Server responded with HTTP {response.status_code} for {url}. Halting further requests to {domain}.")
                self.log_decision(source_id, url, "DENIED", f"Received HTTP {response.status_code} - degraded gracefully without retry.")
                return None

            if response.status_code != 200:
                logger.warning(f"Received non-200 HTTP {response.status_code} for {url}")
                return None

            return response

        except Exception as e:
            logger.error(f"Network error fetching {url}: {e}")
            self.log_decision(source_id, url, "DENIED", f"Network error: {e!s}")
            return None

    def get_audit_logs(self, limit: int = 100) -> list[dict[str, Any]]:
        return [entry.to_dict() for entry in self.audit_log[-limit:]]
