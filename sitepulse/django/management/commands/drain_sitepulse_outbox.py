from __future__ import annotations

import time

from django.core.management.base import BaseCommand
from django.db import OperationalError, ProgrammingError

from sitepulse.django.delivery import drain_outbox


class Command(BaseCommand):
    help = "Send pending SitePulse outbox batches."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--limit", type=int, default=100)
        parser.add_argument("--loop", action="store_true")
        parser.add_argument("--sleep", type=float, default=5.0)

    def handle(self, *args, **options) -> None:
        while True:
            try:
                sent = drain_outbox(limit=options["limit"])
            except (OperationalError, ProgrammingError) as exc:
                if not options["loop"]:
                    raise
                self.stdout.write(f"Outbox is not ready yet: {exc}")
            else:
                self.stdout.write(self.style.SUCCESS(f"Sent {sent} batch(es)."))
            if not options["loop"]:
                return
            time.sleep(options["sleep"])
