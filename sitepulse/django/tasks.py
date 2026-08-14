from __future__ import annotations

try:
    from celery import shared_task
except ImportError:  # pragma: no cover
    shared_task = None

from .delivery import drain_outbox, prune_outbox


if shared_task:

    @shared_task
    def drain_sitepulse_outbox(limit: int = 100) -> int:
        return drain_outbox(limit=limit)

    @shared_task
    def prune_sitepulse_outbox(older_than_days: int | None = None) -> int:
        if older_than_days is None:
            return prune_outbox()
        return prune_outbox(older_than_days=older_than_days)
