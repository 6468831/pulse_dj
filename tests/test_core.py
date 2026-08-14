from __future__ import annotations

import json

from django.test import SimpleTestCase

from sitepulse.fingerprints import browser_signature, normalize_features
from sitepulse.redaction import redact
from sitepulse.signing import sign_batch, verify_signature


class SigningTests(SimpleTestCase):
    def test_hmac_verification(self) -> None:
        raw = json.dumps({"batch_id": "b1", "events": []}, separators=(",", ":")).encode()
        signature = sign_batch("secret", "123", "b1", raw)

        assert verify_signature("secret", "123", "b1", raw, signature)
        assert not verify_signature("secret", "123", "b1", raw + b" ", signature)


class RedactionTests(SimpleTestCase):
    def test_recursive_redaction(self) -> None:
        value = {"ok": "kept", "nested": {"password": "hidden", "card_number": "4111"}}

        assert redact(value) == {
            "ok": "kept",
            "nested": {"password": "[Redacted]", "card_number": "[Redacted]"},
        }


class FingerprintTests(SimpleTestCase):
    def test_fingerprint_normalization_is_stable(self) -> None:
        left = {"browser": " Chrome ", "languages": ["EN-US", "RU"], "nothing": None}
        right = {"languages": ["en-us", "ru"], "browser": "chrome"}

        assert normalize_features(left) == normalize_features(right)
        assert browser_signature("project-secret", left).startswith("bf_")
