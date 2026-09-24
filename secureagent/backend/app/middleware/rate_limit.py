"""
Rate limiting middleware using SlowAPI.
Keyed by user_id (extracted from validated JWT), not by IP.
Falls back to IP if no authenticated user (e.g. health check).
"""
from fastapi import Request
from slowapi import Limiter


def _rate_limit_key(request: Request) -> str:
    """
    Use the validated user_id from request.state if the auth middleware
    has already populated it; otherwise fall back to client IP.
    """
    user_id = getattr(request.state, "user_id", None)
    if user_id:
        return f"user:{user_id}"
    # Fallback — should not reach here for authenticated endpoints
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return f"ip:{forwarded.split(',')[0].strip()}"
    return f"ip:{request.client.host if request.client else 'unknown'}"


limiter = Limiter(key_func=_rate_limit_key)
