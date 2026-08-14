from __future__ import annotations

import time

from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Wait until the configured database accepts connections."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--timeout", type=int, default=60)

    def handle(self, *args, **options) -> None:
        deadline = time.monotonic() + options["timeout"]
        last_error = ""
        while time.monotonic() < deadline:
            try:
                connection.ensure_connection()
            except Exception as exc:  # pragma: no cover - depends on service startup timing
                last_error = str(exc)
                time.sleep(1)
            else:
                self.stdout.write(self.style.SUCCESS("Database is ready."))
                return
        raise RuntimeError(f"Database did not become ready: {last_error}")
