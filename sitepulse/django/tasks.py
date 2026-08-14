from __future__ import annotations

try:
    from celery import shared_task
except ImportError:  # pragma: no cover
    shared_task = None

from .delivery import drain_outbox


if shared_task:

    @shared_task
    def drain_sitepulse_outbox(limit: int = 100) -> int:
        return drain_outbox(limit=limit)
