from __future__ import annotations

import json
from typing import Any
from urllib import request as urlrequest
from uuid import uuid4

from django.db import transaction
from django.utils import timezone

from sitepulse.signing import now_timestamp, sign_batch

from .models import OutboxBatch
from .settings import sitepulse_setting


def build_batch(events: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "project_id": sitepulse_setting("PROJECT_ID"),
        "batch_id": str(uuid4()),
        "events": events,
    }


def sign_payload(batch: dict[str, Any]) -> tuple[bytes, dict[str, str]]:
    raw_body = json.dumps(batch, separators=(",", ":"), sort_keys=True).encode()
    timestamp = now_timestamp()
    signature = sign_batch(sitepulse_setting("SECRET"), timestamp, batch["batch_id"], raw_body)
    return raw_body, {
        "Content-Type": "application/json",
        "X-SitePulse-Timestamp": timestamp,
        "X-SitePulse-Signature": signature,
        "X-SitePulse-Batch": batch["batch_id"],
    }


def enqueue_or_send(events: list[dict[str, Any]]) -> str | None:
    if not events:
        return None
    if not sitepulse_setting("PROJECT_ID"):
        # Unconfigured host: queueing here would fill the outbox with batches that
        # fail as unknown_project on every drain and die after eight attempts.
        return None
    batch = build_batch(events)
    mode = sitepulse_setting("DELIVERY_MODE")
    if mode == "synchronous":
        send_batch(batch)
    else:
        OutboxBatch.objects.create(batch_id=batch["batch_id"], payload=batch)
        dispatch_drain()
    return batch["batch_id"]


def dispatch_drain() -> None:
    """Hand the row we just wrote to a worker now, rather than waiting for a poll.

    This keeps what the outbox is for — the row is committed before anything is
    sent, so a broker that is down, a worker that dies mid-send or a central
    server that is unreachable all lose nothing — while removing the lag that
    made the outbox behave like a queue instead of a transport.

    ``on_commit`` matters: dispatched any earlier, a worker can pick the task up
    and query for a row the sending transaction has not committed yet, find
    nothing, and report success over an empty table.

    Every failure here is swallowed on purpose. The row is already durable and a
    periodic drain will collect it, and an analytics transport must never be able
    to raise inside the request that produced the event — least of all a payment
    webhook.
    """
    try:
        from .tasks import drain_sitepulse_outbox
    except ImportError:  # celery is not installed in this host
        return

    def send_now() -> None:
        try:
            drain_sitepulse_outbox.delay()
        except Exception:  # noqa: BLE001 — broker unreachable; the poll will catch it
            pass

    transaction.on_commit(send_now)


def send_batch(batch: dict[str, Any]) -> None:
    raw_body, headers = sign_payload(batch)
    req = urlrequest.Request(sitepulse_setting("INGEST_URL"), data=raw_body, headers=headers, method="POST")
    with urlrequest.urlopen(req, timeout=5) as response:
        if response.status >= 400:
            raise RuntimeError(f"ingest failed: {response.status}")


def drain_outbox(limit: int = 100) -> int:
    sent = 0
    pending = OutboxBatch.objects.filter(
        status=OutboxBatch.STATUS_PENDING,
        next_attempt_at__lte=timezone.now(),
    ).order_by("created_at")[:limit]
    for row in pending:
        try:
            send_batch(row.payload)
        except Exception as exc:  # pragma: no cover - exercised with network in integration
            row.attempts += 1
            row.last_error = str(exc)[:2000]
            if row.attempts >= 8:
                row.status = OutboxBatch.STATUS_DEAD
            else:
                delay = min(3600, 2 ** row.attempts)
                row.next_attempt_at = timezone.now() + timezone.timedelta(seconds=delay)
            row.save(update_fields=["attempts", "last_error", "status", "next_attempt_at"])
        else:
            row.status = OutboxBatch.STATUS_SENT
            row.sent_at = timezone.now()
            row.save(update_fields=["status", "sent_at"])
            sent += 1
    return sent
