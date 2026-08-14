from __future__ import annotations

from typing import Any

from sitepulse.signing import scoped_hmac


def get_local_user_id(request: Any) -> str | None:
    user = getattr(request, "user", None)
    if not user or not getattr(user, "is_authenticated", False):
        return None
    return str(user.pk)


def scoped_user_hash(project_secret: str, local_user_id: str) -> str:
    return scoped_hmac(project_secret, local_user_id, "uh_")
