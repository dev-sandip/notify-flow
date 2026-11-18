from django.contrib import admin

from apps.events.models import OutboxEvent

from .models import EventAudit

admin.site.register(EventAudit)

@admin.register(OutboxEvent)
class OutboxEventAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "event_type",
        "aggregate_type",
        "aggregate_id",
        "attempts",
        "published_at",
        "created_at",
    )

    list_filter = (
        "event_type",
        "aggregate_type",
        "published_at",
    )

    search_fields = (
        "id",
        "aggregate_id",
        "event_type",
    )

    readonly_fields = (
        "id",
        "created_at",
        "occurred_at",
        "published_at",
    )

    ordering = ("-created_at",)
