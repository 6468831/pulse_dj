from __future__ import annotations

import hashlib
import hmac
import time


def now_timestamp() -> str:
    return str(int(time.time()))


def sign_batch(secret: str, timestamp: str, batch_id: str, raw_body: bytes) -> str:
    message = timestamp.encode() + b"." + batch_id.encode() + b"." + raw_body
    return hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()


def verify_signature(secret: str, timestamp: str, batch_id: str, raw_body: bytes, signature: str) -> bool:
    expected = sign_batch(secret, timestamp, batch_id, raw_body)
    return hmac.compare_digest(expected, signature)


def scoped_hmac(secret: str, value: str, prefix: str) -> str:
    digest = hmac.new(secret.encode(), value.encode(), hashlib.sha256).hexdigest()
    return f"{prefix}{digest}"
