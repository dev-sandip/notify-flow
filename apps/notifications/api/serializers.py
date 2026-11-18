from rest_framework import serializers

from apps.notifications.models import (
    DeliveryAttempt,
    Notification,
)


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
        read_only_fields = ["id", "status", "created_at"]

    def validate_scheduled_at(self, value):
        from django.utils import timezone

        if value and value <= timezone.now():
            raise serializers.ValidationError("Scheduled time must be in the future.")

        return value

    def create(self, validated_data):
        return Notification.objects.create(
            user=self.context["request"].user,
            **validated_data,
        )


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
