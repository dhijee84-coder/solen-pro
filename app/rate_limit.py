"""In-process rate limiter. Sufficient for a single uvicorn worker.
For multi-process production, put a reverse-proxy or Redis limiter in front
(see docs/DEPLOYMENT.md)."""
import threading
import time
from typing import Callable, Optional

from fastapi import HTTPException, Request, status

from .config import settings

_lock = threading.Lock()
_hits: dict[str, list[float]] = {}


def get_client_ip(request: Request) -> str:
    if settings.trusted_proxy:
        forwarded = request.headers.get("x-forwarded-for") or ""
        if forwarded:
            return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host or "unknown"
    return "unknown"


def check(key: str, limit: int, window_seconds: int) -> bool:
    now = time.time()
    with _lock:
        recent = [t for t in _hits.get(key, []) if now - t < window_seconds]
        if len(recent) >= limit:
            _hits[key] = recent
            return False
        recent.append(now)
        _hits[key] = recent
        return True


def reset():
    """Used by tests."""
    with _lock:
        _hits.clear()


def limiter(name: str, limit: Optional[int] = None, window: Optional[int] = None,
            extra_key: Optional[Callable[[Request], str]] = None):
    """FastAPI dependency that 429s when the caller exceeds the window."""
    def _dep(request: Request):
        if not settings.rate_limit_enabled:
            return
        cap = limit if limit is not None else 20
        win = window if window is not None else settings.rate_limit_window_seconds
        ip = get_client_ip(request)
        key = f"{name}:{ip}"
        if extra_key:
            key = f"{key}:{extra_key(request)}"
        if not check(key, cap, win):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please wait a few minutes and try again.",
            )
    return _dep
