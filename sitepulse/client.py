from __future__ import annotations

from contextvars import ContextVar
from typing import Any
from uuid import uuid4

_current_request: ContextVar[Any | None] = ContextVar("sitepulse_request", default=None)


def bind_request(request: Any | None) -> None:
    _current_request.set(request)


def track(
    event_name: str,
    *,
    local_user_id: str | None = None,
    properties: dict[str, Any] | None = None,
) -> None:
    request = _current_request.get()
    if request is not None and local_user_id is None:
        resolver = getattr(request, "sitepulse_get_local_user_id", None)
        if resolver:
            local_user_id = resolver()

    event = {
        "schema_version": 1,
        "event_id": str(uuid4()),
        "event_name": event_name,
        "local_user_id": local_user_id,
        "properties": properties or {},
    }
    if request is not None and hasattr(request, "sitepulse_backend_events"):
        request.sitepulse_backend_events.append(event)
