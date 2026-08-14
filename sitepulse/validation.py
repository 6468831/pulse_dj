from __future__ import annotations

import re
from typing import Any

EVENT_RE = re.compile(r"^[a-z][a-z0-9_:.:-]{0,127}$")


def valid_event_name(name: str | None) -> bool:
    return bool(name and EVENT_RE.match(name))


def list_depth(value: Any, depth: int = 0) -> int:
    if not isinstance(value, dict | list):
        return depth
    if isinstance(value, list):
        return max([depth, *(list_depth(item, depth + 1) for item in value[:100])])
    return max([depth, *(list_depth(item, depth + 1) for item in value.values())])
