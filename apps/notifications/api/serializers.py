from django.db import transaction
from rest_framework import serializers

from apps.notifications.models import (
    DeliveryAttempt,
    Notification,
)
from apps.notifications.tasks import send_notification_task


class NotificationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            "id",
            "recipient_email",
            "subject",
            "body",
            "scheduled_at",
            "status",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "created_at",
        ]

    def validate_scheduled_at(self, value):
        from django.utils import timezone

        if value and value <= timezone.now():
            raise serializers.ValidationError("Scheduled time must be in the future.")

        return value

    def create(self, validated_data):
        notification = Notification.objects.create(
            user=self.context["request"].user,
            **validated_data,
        )

        notification.status = "QUEUED"
        notification.save(update_fields=["status", "updated_at"])

        notification_id = str(notification.id)
        scheduled_at = notification.scheduled_at

        def enqueue_notification():
            if scheduled_at:
                send_notification_task.apply_async(
                    args=[notification_id],
                    eta=scheduled_at,
                )
            else:
                send_notification_task.delay(notification_id)

        # Only enqueue after the database transaction commits.
        transaction.on_commit(enqueue_notification)

        return notification


class DeliveryAttemptSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryAttempt
        fields = [
            "id",
            "attempt_number",
            "status",
            "error_message",
            "started_at",
            "completed_at",
        ]


class NotificationSerializer(serializers.ModelSerializer):
    delivery_attempts = DeliveryAttemptSerializer(many=True, read_only=True)

    class Meta:
        model = Notification
        fields = [
            "id",
            "recipient_email",
            "subject",
            "body",
            "status",
            "scheduled_at",
            "attempt_count",
            "last_error",
            "sent_at",
            "created_at",
            "updated_at",
            "delivery_attempts",
        ]
