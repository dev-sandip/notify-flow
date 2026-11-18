
import logging
from datetime import timedelta

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from apps.events.models import OutboxEvent
from apps.events.publisher import (
    claim_pending_events,
    release_event,
    PUBLISHER_ID,
)
from apps.events.kafka_producer import publish_outbox_event
logger = logging.getLogger(__name__)

MAX_PUBLISH_ATTEMPTS = 10


def publish_event(event: OutboxEvent):
    publish_outbox_event(event)


@shared_task(name="events.publish_pending")
def publish_pending_events():
    events = claim_pending_events()

    published_count = 0
    failed_count = 0

    for event in events:
        try:
            publish_event(event)

            # Only mark published after broker acknowledgement.
            with transaction.atomic():
                OutboxEvent.objects.filter(
                    id=event.id,
                    locked_by=PUBLISHER_ID,
                    published_at__isnull=True,
                ).update(
                    published_at=timezone.now(),
                    locked_at=None,
                    locked_by=None,
                    last_error=None,
                )

            published_count += 1

        except Exception as exc:
            failed_count += 1

            error_message = str(exc)

            with transaction.atomic():
                current_event = (
                    OutboxEvent.objects.select_for_update()
                    .filter(id=event.id)
                    .first()
                )

                if current_event is None:
                    continue

                current_event.attempts += 1
                current_event.last_error = error_message
                current_event.locked_at = None
                current_event.locked_by = None

                if current_event.attempts >= MAX_PUBLISH_ATTEMPTS:
                    # Stop automatic retries after the limit.
                    current_event.next_attempt_at = (
                        timezone.now() + timedelta(days=3650)
                    )
                else:
                    delay = min(
                        30 * (2 ** (current_event.attempts - 1)),
                        3600,
                    )

                    current_event.next_attempt_at = (
                        timezone.now() + timedelta(seconds=delay)
                    )

                current_event.save(
                    update_fields=[
                        "attempts",
                        "last_error",
                        "locked_at",
                        "locked_by",
                        "next_attempt_at",
                    ]
                )

            logger.exception(
                "Failed to publish outbox event %s.",
                event.id,
            )

    logger.info(
        "Outbox publishing finished. Published: %s, Failed: %s",
        published_count,
        failed_count,
    )

    return {
        "claimed": len(events),
        "published": published_count,
        "failed": failed_count,
    }
