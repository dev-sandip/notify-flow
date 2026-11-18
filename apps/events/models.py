import uuid

from django.db import models
from django.utils import timezone


class OutboxEvent(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    event_type = models.CharField(max_length=100)

    aggregate_type = models.CharField(max_length=100)

    aggregate_id = models.CharField(max_length=100)

    payload = models.JSONField()

    schema_version = models.PositiveSmallIntegerField(default=1)

    occurred_at = models.DateTimeField(default=timezone.now)

    created_at = models.DateTimeField(auto_now_add=True)

    published_at = models.DateTimeField(null=True, blank=True)

    attempts = models.PositiveIntegerField(default=0)

    next_attempt_at = models.DateTimeField(default=timezone.now)

    last_error = models.TextField(null=True, blank=True)
    locked_at = models.DateTimeField(null=True, blank=True)

    locked_by = models.CharField(
        max_length=100,
        null=True,
        blank=True,
    )





    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(
                fields=["published_at", "next_attempt_at", "created_at"],
                name="outbox_pending_idx",
            ),
            models.Index(
                fields=["aggregate_type", "aggregate_id"],
                name="outbox_aggregate_idx",
            ),
        ]

    def __str__(self):
        return f"{self.event_type} - {self.aggregate_id}"


class EventAudit(models.Model):
    id = models.BigAutoField(primary_key=True)

    event_id = models.UUIDField(unique=True)

    event_type = models.CharField(max_length=100)
    aggregate_type = models.CharField(max_length=100)
    aggregate_id = models.CharField(max_length=100)

    schema_version = models.PositiveSmallIntegerField(default=1)
    payload = models.JSONField()

    occurred_at = models.DateTimeField()
    consumed_at = models.DateTimeField(auto_now_add=True)

    kafka_topic = models.CharField(max_length=255)
    kafka_partition = models.IntegerField()
    kafka_offset = models.BigIntegerField()

    class Meta:
        ordering = ["-occurred_at"]
        indexes = [
            models.Index(
                fields=["aggregate_type", "aggregate_id", "occurred_at"],
                name="audit_aggregate_time_idx",
            ),
            models.Index(
                fields=["event_type", "occurred_at"],
                name="audit_type_time_idx",
            ),
        ]

    def __str__(self):
        return f"{self.event_type} ({self.event_id})"
