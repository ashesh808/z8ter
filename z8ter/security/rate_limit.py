"""Rate limiting middleware for Z8ter.

This module provides IP-based rate limiting to protect against brute force
attacks, credential stuffing, and DoS attempts.

Features:
- In-memory storage with automatic cleanup of old entries
- Configurable rate limits per path or global
- Returns 429 Too Many Requests when limit exceeded
- Includes Retry-After header in response

Security considerations:
- Rate limiting is per-IP by default; consider proxy headers (X-Forwarded-For)
- In production, consider using Redis for distributed rate limiting
- Be aware of shared IPs (NAT, corporate networks)
"""

import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Callable, Sequence

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


@dataclass
class RateLimitConfig:
    """Configuration for a rate limit rule.

    Attributes:
        requests: Maximum number of requests allowed
        window_seconds: Time window in seconds
        paths: List of path prefixes this rule applies to (None = global)
    """

    requests: int
    window_seconds: int
    paths: Sequence[str] | None = None


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware.

    Tracks request counts per IP address within configurable time windows.
    When the limit is exceeded, returns 429 Too Many Requests.

    Configuration:
        requests_per_minute: Global rate limit (default: 60)
        burst_size: Maximum burst allowance above the rate (default: 10)
        exempt_paths: List of path prefixes to skip rate limiting
        rules: List of RateLimitConfig for path-specific limits

    Usage:
        # Simple global limit
        app.add_middleware(
            RateLimitMiddleware,
            requests_per_minute=60,
        )

        # With path-specific rules
        app.add_middleware(
            RateLimitMiddleware,
            requests_per_minute=60,
            rules=[
                RateLimitConfig(requests=5, window_seconds=60, paths=["/login", "/register"]),
            ],
        )
    """

    def __init__(
        self,
        app,
        requests_per_minute: int = 60,
        burst_size: int = 10,
        exempt_paths: Sequence[str] | None = None,
        rules: Sequence[RateLimitConfig] | None = None,
    ) -> None:
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.burst_size = burst_size
        self.exempt_paths = list(exempt_paths or [])
        self.rules = list(rules or [])

        # Storage: {key: [(timestamp, count), ...]}
        self._requests: dict[str, list[tuple[float, int]]] = defaultdict(list)
        self._last_cleanup = time.time()
        self._cleanup_interval = 60  # Cleanup every 60 seconds

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request, considering proxies."""
        # Check X-Forwarded-For header (common with reverse proxies)
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            # Take the first IP (client IP)
            return forwarded.split(",")[0].strip()

        # Check X-Real-IP header
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip.strip()

        # Fallback to direct client
        if request.client:
            return request.client.host

        return "unknown"

    def _is_exempt(self, path: str) -> bool:
        """Check if path is exempt from rate limiting."""
        return any(path.startswith(exempt) for exempt in self.exempt_paths)

    def _get_rule_for_path(self, path: str) -> RateLimitConfig | None:
        """Get the most specific rate limit rule for a path."""
        for rule in self.rules:
            if rule.paths:
                if any(path.startswith(p) for p in rule.paths):
                    return rule
        return None

    def _cleanup_old_entries(self) -> None:
        """Remove expired entries from storage."""
        now = time.time()
        if now - self._last_cleanup < self._cleanup_interval:
            return

        # Find the oldest window we need to keep
        max_window = max(
            (r.window_seconds for r in self.rules),
            default=60,
        )
        max_window = max(max_window, 60)  # At least 60 seconds
        cutoff = now - max_window

        # Clean up each key
        keys_to_delete = []
        for key, entries in self._requests.items():
            self._requests[key] = [(ts, count) for ts, count in entries if ts > cutoff]
            if not self._requests[key]:
                keys_to_delete.append(key)

        for key in keys_to_delete:
            del self._requests[key]

        self._last_cleanup = now

    def _count_requests(self, key: str, window_seconds: int) -> int:
        """Count requests within the time window."""
        now = time.time()
        cutoff = now - window_seconds
        return sum(count for ts, count in self._requests[key] if ts > cutoff)

    def _record_request(self, key: str) -> None:
        """Record a new request."""
        now = time.time()
        self._requests[key].append((now, 1))

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Response]
    ) -> Response:
        # Run cleanup periodically
        self._cleanup_old_entries()

        # Skip exempt paths
        if self._is_exempt(request.url.path):
            return await call_next(request)

        client_ip = self._get_client_ip(request)

        # Check path-specific rules first
        rule = self._get_rule_for_path(request.url.path)

        if rule:
            # Path-specific rate limit
            key = f"{client_ip}:{rule.paths[0] if rule.paths else 'global'}"
            max_requests = rule.requests
            window = rule.window_seconds
        else:
            # Global rate limit
            key = f"{client_ip}:global"
            max_requests = self.requests_per_minute + self.burst_size
            window = 60

        # Count requests in window
        count = self._count_requests(key, window)

        if count >= max_requests:
            # Calculate retry-after time
            entries = self._requests[key]
            if entries:
                oldest_in_window = min(ts for ts, _ in entries if ts > time.time() - window)
                retry_after = int(oldest_in_window + window - time.time()) + 1
            else:
                retry_after = window

            return JSONResponse(
                {
                    "ok": False,
                    "error": {
                        "message": "Too many requests. Please try again later.",
                        "retry_after": retry_after,
                    },
                },
                status_code=429,
                headers={"Retry-After": str(retry_after)},
            )

        # Record this request
        self._record_request(key)

        return await call_next(request)
