from __future__ import annotations

from typing import Any

from sitepulse.client import bind_request
from sitepulse.redaction import redact
from sitepulse.signing import scoped_hmac

from .delivery import enqueue_or_send
from .identity import get_local_user_id
from .settings import sitepulse_setting


def enrich_backend_events(request: Any, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Give server-side events the identity fields the central server joins on.

    ``track()`` runs deep inside a view and knows at most a local user id. The
    central server only creates an AuthenticatedIdentity when an event carries a
    scoped_user_hash as well, so without this an event would be stored and then
    never appear in that user's journey.

    The relay view does the same enrichment for events posted by the browser.
    Events raised on a request that never reaches the relay — a payment webhook
    called server-to-server, say — have no other chance to get it, and those are
    exactly the events worth trusting.
    """
    secret = sitepulse_setting("SECRET")
    cookie_anonymous_id = request.COOKIES.get(sitepulse_setting("COOKIE_NAME"))
    enriched: list[dict[str, Any]] = []
    for event in events:
        local_user_id = event.get("local_user_id")
        if not event.get("anonymous_id"):
            # A webhook carries the payment provider's cookies, not the buyer's,
            # so this is usually None. The local user id is what identifies them.
            event["anonymous_id"] = cookie_anonymous_id
        event["scoped_user_hash"] = (
            scoped_hmac(secret, local_user_id, "uh_") if local_user_id else None
        )
        enriched.append(redact(event))
    return enriched


class SitePulseMiddleware:
    def __init__(self, get_response: Any) -> None:
        self.get_response = get_response

    def __call__(self, request: Any) -> Any:
        request.sitepulse_backend_events = []
        request.sitepulse_get_local_user_id = lambda: get_local_user_id(request)
        bind_request(request)
        try:
            response = self.get_response(request)
            events = getattr(request, "sitepulse_backend_events", [])
            enqueue_or_send(enrich_backend_events(request, events))
            return response
        finally:
            bind_request(None)
