"""
API integration tests for FinancialWatch FastAPI backend.
Validates authentication, input validation, seed endpoints, and SSE trace streaming.
"""
import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.main import app

VALID_API_KEY = "fw-test-access-key-2026"

@pytest.mark.asyncio
async def test_health_check():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

@pytest.mark.asyncio
async def test_api_key_security_enforcement():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Missing API key -> 401
        resp_no_key = await client.get("/api/posts")
        assert resp_no_key.status_code == 401

        # 2. Invalid API key -> 403
        resp_bad_key = await client.get("/api/posts", headers={"X-API-Key": "invalid-secret"})
        assert resp_bad_key.status_code == 403

        # 3. Valid API key -> 200
        resp_valid = await client.get("/api/posts", headers={"X-API-Key": VALID_API_KEY})
        assert resp_valid.status_code == 200

@pytest.mark.asyncio
async def test_get_seed_posts():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/posts/seed", headers={"X-API-Key": VALID_API_KEY})
        assert resp.status_code == 200
        seeds = resp.json()
        assert len(seeds) >= 25
        assert "id" in seeds[0]
        assert "gold_label" in seeds[0]
        assert "expected_verdict" in seeds[0]

@pytest.mark.asyncio
async def test_analyze_stream_execution():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "text": "BREAKING: CBN has revoked the license of Apex Horizon Example Bank! Withdraw your deposits!",
            "platform": "Paste Intake",
            "source_adapter": "PasteAdapter"
        }
        resp = await client.post(
            "/api/posts/analyze",
            json=payload,
            headers={"X-API-Key": VALID_API_KEY}
        )
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]

        body_text = resp.text
        # Verify SSE structure
        assert "event: pipeline_start" in body_text
        assert "event: agent_trace" in body_text
        assert "event: ping" in body_text
        assert "event: pipeline_complete" in body_text
        assert "Apex Horizon Example Bank" in body_text

@pytest.mark.asyncio
async def test_root_static_mount():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/")
        assert resp.status_code == 200
        # Check that it serves HTML content
        assert "html" in resp.headers.get("content-type", "") or "FinancialWatch" in resp.text

