from __future__ import annotations

from typing import Any

from django.conf import settings


DEFAULTS = {
    "PROJECT_ID": "",
    "SECRET": "",
    "INGEST_URL": "",
    "PUBLIC_EVENT_PATH": "api/runtime/events/",
    "COOKIE_NAME": "_rtid",
    "DELIVERY_MODE": "database_outbox",
    "FINGERPRINT_LEVEL": "basic",
    "NETWORK_PROVIDER": "disabled",
}


def sitepulse_setting(name: str) -> Any:
    config = getattr(settings, "SITEPULSE", {})
    return config.get(name, DEFAULTS[name])
