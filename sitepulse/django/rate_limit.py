from __future__ import annotations

import hashlib

from django.core.cache import cache
from django.http import HttpRequest


def rate_limited(request: HttpRequest, *, limit: int = 120, window_seconds: int = 60) -> bool:
    ip_address = request.META.get("HTTP_X_FORWARDED_FOR", request.META.get("REMOTE_ADDR", "unknown"))
    fingerprint = hashlib.sha256(f"{request.path}:{ip_address}".encode()).hexdigest()
    key = f"sitepulse:relay-rate:{fingerprint}"
    added = cache.add(key, 1, timeout=window_seconds)
    if added:
        return False
    try:
        return cache.incr(key) > limit
    except ValueError:
        cache.set(key, 1, timeout=window_seconds)
        return False
