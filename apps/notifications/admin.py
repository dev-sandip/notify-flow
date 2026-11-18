from django.contrib import admin

from .models import DeliveryAttempt, Notification


class DeliveryAttemptInline(admin.TabularInline):
    model = DeliveryAttempt
    extra = 0
    readonly_fields = (
        "attempt_number",
        "status",
        "error_message",
        "started_at",
        "completed_at",
    )


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "recipient_email",
        "subject",
        "status",
        "attempt_count",
        "created_at",
    )

    list_filter = ("status", "created_at")
    search_fields = ("recipient_email", "subject", "user__email")
    readonly_fields = (
        "id",
        "attempt_count",
        "last_error",
        "sent_at",
        "created_at",
        "updated_at",
    )

    inlines = [DeliveryAttemptInline]


@admin.register(DeliveryAttempt)
class DeliveryAttemptAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "notification",
        "attempt_number",
        "status",
        "started_at",
        "completed_at",
    )

    list_filter = ("status",)
    readonly_fields = (
        "id",
        "notification",
        "attempt_number",
        "status",
        "error_message",
        "started_at",
        "completed_at",
    )
