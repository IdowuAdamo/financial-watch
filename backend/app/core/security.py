"""
Security middleware, API Key authentication, rate limiting, and input caps.
Guards the FinancialWatch API from being used as an open LLM proxy.
"""
import hmac
import os
import time

from fastapi import HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)
EXPECTED_API_KEY = os.getenv("API_ACCESS_KEY", "fw-test-access-key-2026")
MAX_POST_LENGTH = 2000

class RateLimiter:
    """Token bucket / sliding window rate limiter keyed by API key or client IP."""
    def __init__(self, max_requests_per_minute: int = 30):
        self.max_requests = max_requests_per_minute
        self._history: dict[str, list] = {}

    def is_rate_limited(self, identifier: str) -> tuple[bool, int]:
        now = time.time()
        window = 60.0
        
        timestamps = self._history.get(identifier, [])
        # Prune old timestamps
        timestamps = [t for t in timestamps if now - t < window]
        
        if len(timestamps) >= self.max_requests:
            retry_after = int(window - (now - timestamps[0]))
            self._history[identifier] = timestamps
            return True, max(1, retry_after)
        
        timestamps.append(now)
        self._history[identifier] = timestamps
        return False, 0

rate_limiter = RateLimiter(max_requests_per_minute=30)

async def verify_api_key(
    request: Request,
    api_key: str | None = Security(API_KEY_HEADER)
) -> str:
    """
    Validates the X-API-Key header using constant-time string comparison.
    Also enforces per-key rate limiting.
    """
    # Allow OPTIONS preflight
    if request.method == "OPTIONS":
        return ""

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing required X-API-Key header."
        )

    expected_key = os.getenv("API_ACCESS_KEY", EXPECTED_API_KEY)
    if not expected_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API_ACCESS_KEY is not configured on the server."
        )

    # Constant-time comparison
    if not hmac.compare_digest(api_key, expected_key):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API Access Key."
        )

    # Rate limiting
    client_ip = request.client.host if request.client else "unknown"
    rate_key = f"{api_key}:{client_ip}"
    limited, retry_after = rate_limiter.is_rate_limited(rate_key)
    if limited:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Try again in {retry_after} seconds.",
            headers={"Retry-After": str(retry_after)}
        )

    return api_key

def validate_post_length(text: str):
    """Enforces strict input length caps on analyzed text."""
    if not text or not text.strip():
        raise HTTPException(status_code=400, detail="Post text cannot be empty.")
    if len(text) > MAX_POST_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Input length {len(text)} exceeds maximum allowed limit of {MAX_POST_LENGTH} characters."
        )
