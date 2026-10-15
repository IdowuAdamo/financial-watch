"""
Unit tests for compliance gate, robots parser, and rate limiter.
"""
import asyncio

import pytest

from memory.compliance.gate import ComplianceGate
from memory.compliance.rate_limiter import DomainRateLimiter
from memory.compliance.robots import RobotsCacheEntry, RobotsComplianceManager


@pytest.mark.asyncio
async def test_robots_http_403_marked_manual_only():
    """Verify that HTTP 403 on robots.txt immediately marks domain as manual-only."""
    manager = RobotsComplianceManager(
        user_agent="FinancialWatchBot/1.0",
        contact_url="https://github.com/client/financial-watch"
    )
    # Manually inject 403 cache entry
    manager._cache["africacheck.org"] = RobotsCacheEntry(parser=None, status_code=403, crawl_delay=0.0)

    # Fake client is not called because cache is warm
    allowed, reason, delay = await manager.is_allowed(None, "https://africacheck.org/fact-checks/sample")
    assert allowed is False
    assert "403" in reason
    assert "manual-only" in reason

@pytest.mark.asyncio
async def test_robots_http_404_conservative_mode():
    """Verify that 404 on robots.txt allows conservative crawl mode."""
    manager = RobotsComplianceManager(
        user_agent="FinancialWatchBot/1.0",
        contact_url="https://github.com/client/financial-watch"
    )
    manager._cache["sec.gov.ng"] = RobotsCacheEntry(parser=None, status_code=404, crawl_delay=10.0)

    allowed, reason, delay = await manager.is_allowed(None, "https://sec.gov.ng/circulars/sample")
    assert allowed is True
    assert delay == 10.0
    assert "conservative" in reason.lower()

@pytest.mark.asyncio
async def test_domain_rate_limiter():
    """Verify that domain rate limiter enforces minimum intervals."""
    limiter = DomainRateLimiter(default_interval_seconds=0.1)
    limiter.set_domain_interval("dubawa.org", 0.2)

    t0 = asyncio.get_event_loop().time()
    await limiter.wait_for_domain("dubawa.org")
    await limiter.wait_for_domain("dubawa.org")
    elapsed = asyncio.get_event_loop().time() - t0

    assert elapsed >= 0.18 # Honored ~0.2s interval

def test_compliance_decision_logging():
    """Verify that compliance gate records full audit log entries."""
    gate = ComplianceGate()
    gate.log_decision("cbn", "https://www.cbn.gov.ng/test", "ALLOWED", "Unit test pass")
    gate.log_decision("africacheck", "https://africacheck.org/test", "DENIED", "HTTP 403 manual only")

    logs = gate.get_audit_logs()
    assert len(logs) == 2
    assert logs[0]["decision"] == "ALLOWED"
    assert logs[1]["decision"] == "DENIED"
