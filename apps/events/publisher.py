
import logging
import uuid
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from apps.events.models import OutboxEvent

logger = logging.getLogger(__name__)

BATCH_SIZE = 100
LOCK_TIMEOUT = timedelta(minutes=5)

PUBLISHER_ID = f"publisher-{uuid.uuid4()}"


def claim_pending_events(batch_size: int = BATCH_SIZE):
    """
    Atomically claim a batch of unpublished events.

    Events with expired locks can be claimed again.
    """

    now = timezone.now()
    expired_lock_time = now - LOCK_TIMEOUT

    with transaction.atomic():
        events = list(
            OutboxEvent.objects.select_for_update(
                skip_locked=True
            )
            .filter(
                published_at__isnull=True,
                next_attempt_at__lte=now,
            )
            .filter(
                locked_at__isnull=True,
            )
            .order_by("created_at")[:batch_size]
        )

        # Also recover events whose publisher crashed
        # while holding a lease.
        expired_events = list(
            OutboxEvent.objects.select_for_update(
                skip_locked=True
            )
            .filter(
                published_at__isnull=True,
                next_attempt_at__lte=now,
                locked_at__lt=expired_lock_time,
            )
            .order_by("created_at")[:max(0, batch_size - len(events))]
        )

        claimed_events = events + expired_events

        for event in claimed_events:
            event.locked_at = now
            event.locked_by = PUBLISHER_ID

        if claimed_events:
            OutboxEvent.objects.bulk_update(
                claimed_events,
                ["locked_at", "locked_by"],
            )

    return claimed_events


def release_event(event: OutboxEvent):
    """
    Release an event after a publishing failure.
    """

    OutboxEvent.objects.filter(
        id=event.id,
        locked_by=PUBLISHER_ID,
        published_at__isnull=True,
    ).update(
        locked_at=None,
        locked_by=None,
    )
