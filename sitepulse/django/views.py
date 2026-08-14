from __future__ import annotations

from typing import Any

from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from sitepulse.fingerprints import browser_signature, http_signature, trusted_network_signature
from sitepulse.redaction import redact
from sitepulse.signing import scoped_hmac
from sitepulse.validation import list_depth, valid_event_name

from .delivery import enqueue_or_send
from .identity import get_local_user_id, scoped_user_hash
from .rate_limit import rate_limited
from .settings import sitepulse_setting

MAX_BODY_BYTES = 256_000
MAX_EVENTS = 100
MAX_PROPERTY_DEPTH = 6


@csrf_exempt
@require_POST
def events(request: HttpRequest) -> JsonResponse:
    if rate_limited(request):
        return JsonResponse({"error": "rate_limited"}, status=429)
    if len(request.body) > MAX_BODY_BYTES:
        return JsonResponse({"error": "payload_too_large"}, status=413)
    body: dict[str, Any] = {}
    try:
        import json

        body = json.loads(request.body or b"{}")
    except ValueError:
        return JsonResponse({"error": "invalid_json"}, status=400)

    local_user_id = get_local_user_id(request)
    secret = sitepulse_setting("SECRET")
    accepted: list[dict[str, Any]] = []

    events_payload = body.get("events", [])
    if not isinstance(events_payload, list) or len(events_payload) > MAX_EVENTS:
        return JsonResponse({"error": "invalid_events"}, status=400)

    rejected = 0
    for event in events_payload:
        if (
            not isinstance(event, dict)
            or not valid_event_name(event.get("event_name"))
            or list_depth(event.get("properties") or {}) > MAX_PROPERTY_DEPTH
        ):
            rejected += 1
            continue
        clean = redact(event)
        clean.pop("local_user_id", None)
        clean["local_user_id"] = local_user_id
        clean["scoped_user_hash"] = scoped_user_hash(secret, local_user_id) if local_user_id else None
        clean["browser_signature"] = browser_signature(secret, clean.get("browser_features"))
        clean["http_signature"] = http_signature(secret, request.META)
        clean["network_signature"] = trusted_network_signature(secret, request.META)
        clean["identity_link"] = {
            "anonymous_id": clean.get("anonymous_id"),
            "local_user_id": local_user_id,
            "scoped_user_hash": clean["scoped_user_hash"],
        }
        accepted.append(clean)

    backend_events = getattr(request, "sitepulse_backend_events", [])
    for event in backend_events:
        event["anonymous_id"] = request.COOKIES.get(sitepulse_setting("COOKIE_NAME"))
        event["local_user_id"] = local_user_id
        event["scoped_user_hash"] = scoped_hmac(secret, local_user_id, "uh_") if local_user_id else None
        accepted.append(redact(event))
    # Consumed and enriched here, so the middleware must not drain them again on
    # the way out — same event_id twice is a wasted batch the central server
    # rejects on its unique (project, event_id).
    del backend_events[:]

    batch_id = enqueue_or_send(accepted)
    return JsonResponse({"accepted": len(accepted), "rejected": rejected, "batch_id": batch_id})
