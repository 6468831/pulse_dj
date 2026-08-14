from __future__ import annotations

from collections.abc import Mapping
from typing import Any

SENSITIVE_PARTS = (
    "password",
    "passwd",
    "token",
    "secret",
    "cookie",
    "authorization",
    "card",
    "cvv",
    "cvc",
    "pan",
)


def redact(value: Any, depth: int = 0, max_depth: int = 6, max_string: int = 1024) -> Any:
    if depth > max_depth:
        return "[Max depth]"
    if isinstance(value, str):
        return value[:max_string]
    if isinstance(value, list):
        return [redact(item, depth + 1, max_depth, max_string) for item in value[:100]]
    if isinstance(value, Mapping):
        clean: dict[str, Any] = {}
        for key, item in list(value.items())[:100]:
            key_text = str(key)[:128]
            if any(part in key_text.lower() for part in SENSITIVE_PARTS):
                clean[key_text] = "[Redacted]"
            else:
                clean[key_text] = redact(item, depth + 1, max_depth, max_string)
        return clean
    if isinstance(value, int | float | bool) or value is None:
        return value
    return str(value)[:max_string]
