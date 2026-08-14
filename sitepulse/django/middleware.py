from __future__ import annotations

from typing import Any

from sitepulse.client import bind_request

from .delivery import enqueue_or_send
from .identity import get_local_user_id


class SitePulseMiddleware:
    def __init__(self, get_response: Any) -> None:
        self.get_response = get_response

    def __call__(self, request: Any) -> Any:
        request.sitepulse_backend_events = []
        request.sitepulse_get_local_user_id = lambda: get_local_user_id(request)
        bind_request(request)
        try:
            response = self.get_response(request)
            enqueue_or_send(getattr(request, "sitepulse_backend_events", []))
            return response
        finally:
            bind_request(None)
