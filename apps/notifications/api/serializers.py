from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from apps.notifications.models import (
    DeliveryAttempt,
    Notification,
    NotificationStatus,
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
        if value and value <= timezone.now():
            raise serializers.ValidationError("Scheduled time must be in the future.")
        return value

    def create(self, validated_data):
        scheduled_at = validated_data.get("scheduled_at")

        # Immediate notifications are queued.
        # Scheduled notifications remain pending.
        initial_status = (
            NotificationStatus.PENDING if scheduled_at else NotificationStatus.QUEUED
        )

        notification = Notification.objects.create(
            user=self.context["request"].user,
            status=initial_status,
            **validated_data,
        )

        # Only immediate notifications are dispatched here.
        if not scheduled_at:
            notification_id = str(notification.id)

            transaction.on_commit(lambda: send_notification_task.delay(notification_id))

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
