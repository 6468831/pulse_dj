from __future__ import annotations

import json
from typing import Any

from .signing import scoped_hmac


def normalize_features(features: dict[str, Any] | None) -> dict[str, Any]:
    if not features:
        return {}
    normalized: dict[str, Any] = {}
    for key, value in sorted(features.items()):
        if value is None:
            continue
        if isinstance(value, str):
            normalized[key] = value.strip().lower()[:256]
        elif isinstance(value, list):
            normalized[key] = [str(item).strip().lower()[:128] for item in value[:20]]
        elif isinstance(value, bool | int | float):
            normalized[key] = value
        else:
            normalized[key] = str(value)[:256]
    return normalized


def browser_signature(project_secret: str, features: dict[str, Any] | None) -> str:
    normalized = normalize_features(features)
    payload = json.dumps(normalized, sort_keys=True, separators=(",", ":"))
    return scoped_hmac(project_secret, payload, "bf_")


def http_signature(project_secret: str, meta: dict[str, str]) -> str:
    keys = [
        "HTTP_USER_AGENT",
        "HTTP_ACCEPT",
        "HTTP_ACCEPT_LANGUAGE",
        "HTTP_SEC_CH_UA",
        "HTTP_SEC_CH_UA_PLATFORM",
        "HTTP_SEC_FETCH_SITE",
        "SERVER_PROTOCOL",
    ]
    payload = "|".join(f"{key}={meta.get(key, '')[:512]}" for key in keys)
    return scoped_hmac(project_secret, payload, "hf_")


def trusted_network_signature(project_secret: str, meta: dict[str, str]) -> str | None:
    values = [
        meta.get("HTTP_X_SITEPULSE_JA3"),
        meta.get("HTTP_X_SITEPULSE_JA4"),
        meta.get("HTTP_X_SITEPULSE_TLS"),
        meta.get("HTTP_CF_TLS_CLIENT_AUTH_CERT_SHA256"),
    ]
    payload = "|".join(value for value in values if value)
    if not payload:
        return None
    return scoped_hmac(project_secret, payload, "nf_")
