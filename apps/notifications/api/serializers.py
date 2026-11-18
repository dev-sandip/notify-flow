from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from apps.notifications.models import (
    DeliveryAttempt,
    Notification,
    NotificationStatus,
)
from apps.notifications.tasks import send_notification_task


from apps.events.services import record_event


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

        initial_status = (
            NotificationStatus.PENDING
            if scheduled_at
            else NotificationStatus.QUEUED
        )

        with transaction.atomic():
            notification = Notification.objects.create(
                user=self.context["request"].user,
                status=initial_status,
                **validated_data,
            )

            record_event(
                event_type="notification.created",
                aggregate_type="notification",
                aggregate_id=str(notification.id),
                payload={
                    "notification_id": str(notification.id),
                    "user_id": str(notification.user_id),
                    "recipient_email": notification.recipient_email,
                    "subject": notification.subject,
                    "status": notification.status,
                    "scheduled_at": (
                        notification.scheduled_at.isoformat()
                        if notification.scheduled_at
                        else None
                    ),
                },
            )

            if not scheduled_at:
                notification_id = str(notification.id)

                transaction.on_commit(
                    lambda: send_notification_task.delay(notification_id)
                )

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
