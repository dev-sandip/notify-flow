import logging

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from apps.notifications.models import (
    Notification,
    NotificationStatus,
)
from apps.notifications.tasks.notification import send_notification_task

logger = logging.getLogger(__name__)

BATCH_SIZE = 100


@shared_task(name="notifications.dispatch_due")
def dispatch_due_notifications():
    notification_ids = []

    with transaction.atomic():
        due_notifications = (
            Notification.objects.select_for_update(skip_locked=True)
            .filter(
                status=NotificationStatus.PENDING,
                scheduled_at__isnull=False,
                scheduled_at__lte=timezone.now(),
            )
            .order_by("scheduled_at", "created_at")[:BATCH_SIZE]
        )

        for notification in due_notifications:
            notification.status = NotificationStatus.QUEUED
            notification.save(update_fields=["status", "updated_at"])

            notification_ids.append(str(notification.id))

        if notification_ids:
            transaction.on_commit(
                lambda ids=notification_ids.copy(): enqueue_notifications(ids)
            )

    logger.info(
        "Dispatched %s due notifications.",
        len(notification_ids),
    )

    return len(notification_ids)


def enqueue_notifications(notification_ids):
    for notification_id in notification_ids:
        try:
            send_notification_task.delay(notification_id)
        except Exception:
            logger.exception(
                "Failed to enqueue notification %s",
                notification_id,
            )
