import uuid

from django.conf import settings
from django.db import models


class NotificationStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    QUEUED = "QUEUED", "Queued"
    PROCESSING = "PROCESSING", "Processing"
    RETRYING = "RETRYING", "Retrying"
    SENT = "SENT", "Sent"
    FAILED = "FAILED", "Failed"
    CANCELLED = "CANCELLED", "Cancelled"


class DeliveryStatus(models.TextChoices):
    PROCESSING = "PROCESSING", "Processing"
    SUCCESS = "SUCCESS", "Success"
    FAILED = "FAILED", "Failed"


class Notification(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )

    recipient_email = models.EmailField()

    subject = models.CharField(max_length=255)

    body = models.TextField()

    status = models.CharField(
        max_length=20,
        choices=NotificationStatus.choices,
        default=NotificationStatus.PENDING,
        db_index=True,
    )

    scheduled_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    attempt_count = models.PositiveSmallIntegerField(default=0)

    last_error = models.TextField(
        null=True,
        blank=True,
    )

    sent_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["user", "-created_at"],
                name="notif_user_created_idx",
            ),
            models.Index(
                fields=["status", "scheduled_at"],
                name="notif_status_sched_idx",
            ),
        ]

    def __str__(self):
        return f"{self.subject} - {self.recipient_email}"


class DeliveryAttempt(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    notification = models.ForeignKey(
        Notification,
        on_delete=models.CASCADE,
        related_name="delivery_attempts",
    )

    attempt_number = models.PositiveSmallIntegerField()

    status = models.CharField(
        max_length=20,
        choices=DeliveryStatus.choices,
        default=DeliveryStatus.PROCESSING,
    )

    error_message = models.TextField(
        null=True,
        blank=True,
    )

    started_at = models.DateTimeField(auto_now_add=True)

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-started_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["notification", "attempt_number"],
                name="unique_notification_attempt",
            ),
        ]

    def __str__(self):
        return f"{self.notification_id} - Attempt {self.attempt_number} - {self.status}"
