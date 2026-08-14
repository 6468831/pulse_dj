from __future__ import annotations

from django.contrib.staticfiles import finders
from django.test import SimpleTestCase


class StaticAssetTests(SimpleTestCase):
    def test_runtime_core_is_packaged_as_django_static_asset(self) -> None:
        assert finders.find("sitepulse/runtime-core.js")
