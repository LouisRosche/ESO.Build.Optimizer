"""
Rate limiting middleware for ESO Build Optimizer API.

Implements per-user rate limiting with configurable limits.
"""

import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.config import settings
from api.models.database import RateLimit, User, get_db


# =============================================================================
# In-Memory Rate Limiter (for development/single-instance)
# =============================================================================

class InMemoryRateLimiter:
    """
    Simple in-memory rate limiter using sliding window.

    For production, use Redis-based rate limiting instead.
    """

    def __init__(self):
        self.requests: dict[str, list[float]] = defaultdict(list)
        self.cleanup_interval = 60  # seconds
        self.last_cleanup = time.time()

    def _cleanup_old_requests(self, key: str, window_seconds: int):
        """Remove requests outside the current window."""
        now = time.time()
        cutoff = now - window_seconds
        self.requests[key] = [t for t in self.requests[key] if t > cutoff]

    def _global_cleanup(self):
        """Periodic cleanup of all old entries."""
        now = time.time()
        if now - self.last_cleanup > self.cleanup_interval:
            for key in list(self.requests.keys()):
                # Keep only requests from the last hour
                cutoff = now - 3600
                self.requests[key] = [t for t in self.requests[key] if t > cutoff]
                if not self.requests[key]:
                    del self.requests[key]
            self.last_cleanup = now

    def is_allowed(
        self,
        key: str,
        max_requests: int,
        window_seconds: int,
    ) -> tuple[bool, int, int]:
        """
        Check if a request is allowed under rate limits.

        Args:
            key: Unique identifier for the rate limit bucket
            max_requests: Maximum requests allowed in window
            window_seconds: Time window in seconds

        Returns:
            Tuple of (is_allowed, remaining_requests, retry_after_seconds)
        """
        self._global_cleanup()
        self._cleanup_old_requests(key, window_seconds)

        current_requests = len(self.requests[key])

        if current_requests >= max_requests:
            # Calculate retry-after
            oldest_request = min(self.requests[key]) if self.requests[key] else time.time()
            retry_after = int(oldest_request + window_seconds - time.time())
            return False, 0, max(1, retry_after)

        # Allow request
        self.requests[key].append(time.time())
        remaining = max_requests - len(self.requests[key])
        return True, remaining, 0

    def get_usage(self, key: str, window_seconds: int) -> int:
        """Get current request count for a key."""
        self._cleanup_old_requests(key, window_seconds)
        return len(self.requests[key])


# Global rate limiter instance
rate_limiter = InMemoryRateLimiter()


# =============================================================================
# Rate Limit Dependencies
# =============================================================================

async def check_rate_limit(
    request: Request,
    user_id: UUID | None = None,
) -> None:
    """
    Check rate limits for a request.

    Args:
        request: FastAPI request object
        user_id: Optional user ID for per-user limits

    Raises:
        HTTPException: If rate limit is exceeded
    """
    # Use user ID if available, otherwise use client IP
    if user_id:
        key = f"user:{user_id}"
    else:
        # Get client IP from request
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"
        key = f"ip:{client_ip}"

    # Add endpoint to key for per-endpoint limits
    endpoint_key = f"{key}:{request.url.path}"

    # Check per-minute limit
    allowed, remaining, retry_after = rate_limiter.is_allowed(
        endpoint_key,
        settings.rate_limit_requests_per_minute,
        60,
    )

    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please slow down.",
            headers={
                "Retry-After": str(retry_after),
                "X-RateLimit-Limit": str(settings.rate_limit_requests_per_minute),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(int(time.time()) + retry_after),
            },
        )

    # Also check burst limit (short window)
    burst_allowed, _, _ = rate_limiter.is_allowed(
        f"{key}:burst",
        settings.rate_limit_burst_size,
        1,  # 1 second window
    )

    if not burst_allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests in a short time. Please wait a moment.",
            headers={
                "Retry-After": "1",
            },
        )


class RateLimitMiddleware:
    """
    Rate limiting middleware for FastAPI.

    Applies rate limits to all requests based on IP or user.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)

        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/api/v1/health"]:
            await self.app(scope, receive, send)
            return

        try:
            # Check rate limit (without user context in middleware)
            await check_rate_limit(request)
            await self.app(scope, receive, send)
        except HTTPException as e:
            # Convert HTTPException to response
            from starlette.responses import JSONResponse
            response = JSONResponse(
                status_code=e.status_code,
                content={"detail": e.detail},
                headers=e.headers,
            )
            await response(scope, receive, send)


def rate_limit_dependency(
    requests_per_minute: int | None = None,
):
    """
    Create a rate limit dependency with custom limits.

    Args:
        requests_per_minute: Custom per-minute limit (uses default if None)

    Returns:
        Dependency function for FastAPI
    """
    limit = requests_per_minute or settings.rate_limit_requests_per_minute

    async def dependency(request: Request):
        key = f"custom:{request.url.path}"

        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"

        full_key = f"ip:{client_ip}:{key}"

        allowed, remaining, retry_after = rate_limiter.is_allowed(
            full_key,
            limit,
            60,
        )

        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
                headers={"Retry-After": str(retry_after)},
            )

    return Depends(dependency)
