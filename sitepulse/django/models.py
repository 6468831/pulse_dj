from __future__ import annotations

from django.db import models
from django.utils import timezone


class OutboxBatch(models.Model):
    STATUS_PENDING = "pending"
    STATUS_SENT = "sent"
    STATUS_DEAD = "dead"

    batch_id = models.CharField(max_length=64, unique=True)
    payload = models.JSONField()
    status = models.CharField(max_length=16, default=STATUS_PENDING)
    attempts = models.PositiveIntegerField(default=0)
    next_attempt_at = models.DateTimeField(default=timezone.now)
    last_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
