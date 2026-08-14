from __future__ import annotations

import time

from django.core.management.base import BaseCommand
from django.db import OperationalError, ProgrammingError

from sitepulse.django.delivery import SENT_RETENTION_DAYS, drain_outbox, prune_outbox


class Command(BaseCommand):
    help = "Send pending SitePulse outbox batches."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--limit", type=int, default=100)
        parser.add_argument("--loop", action="store_true")
        parser.add_argument("--sleep", type=float, default=5.0)
        parser.add_argument(
            "--prune",
            action="store_true",
            help=(
                "Also delete delivered rows older than the retention window. For "
                "hosts without Celery: run this from cron, not with --loop."
            ),
        )
        parser.add_argument("--prune-days", type=int, default=SENT_RETENTION_DAYS)

    def handle(self, *args, **options) -> None:
        if options["prune"]:
            deleted = prune_outbox(older_than_days=options["prune_days"])
            self.stdout.write(f"Pruned {deleted} delivered batch(es).")
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
