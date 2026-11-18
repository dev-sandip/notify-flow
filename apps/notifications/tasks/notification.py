import logging

from celery import shared_task
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from apps.notifications.models import (
    DeliveryAttempt,
    DeliveryStatus,
    Notification,
    NotificationStatus,
)

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name="notifications.send_notification",
    max_retries=2,
    acks_late=True,
)
def send_notification_task(self, notification_id: str):
    """
    Send a notification email.

    max_retries=2 means:
        Attempt 1: initial execution
        Attempt 2: first retry
        Attempt 3: second retry

    Total maximum delivery attempts: 3.
    """

    # Lock the notification while creating its delivery attempt.
    with transaction.atomic():
        try:
            notification = Notification.objects.select_for_update().get(
                id=notification_id
            )
        except Notification.DoesNotExist:
            logger.warning(
                "Notification %s does not exist.",
                notification_id,
            )
            return

        # Do not send notifications that have already finished.
        if notification.status in [
            NotificationStatus.SENT,
            NotificationStatus.FAILED,
            NotificationStatus.CANCELLED,
        ]:
            logger.info(
                "Skipping notification %s with status %s.",
                notification_id,
                notification.status,
            )
            return

        attempt_number = notification.attempt_count + 1

        notification.status = NotificationStatus.PROCESSING
        notification.attempt_count = attempt_number
        notification.last_error = None
        notification.save(
            update_fields=[
                "status",
                "attempt_count",
                "last_error",
                "updated_at",
            ]
        )

        attempt = DeliveryAttempt.objects.create(
            notification=notification,
            attempt_number=attempt_number,
            status=DeliveryStatus.PROCESSING,
        )

        recipient_email = notification.recipient_email
        subject = notification.subject
        body = notification.body

    # Send the email outside the database transaction.
    try:
        sent_count = send_mail(
            subject=subject,
            message=body,
            from_email=None,
            recipient_list=[recipient_email],
            fail_silently=False,
        )

        if sent_count != 1:
            raise RuntimeError("Email backend did not send the message.")

    except Exception as exc:
        error_message = str(exc)

        # Record the failed attempt.
        with transaction.atomic():
            attempt.status = DeliveryStatus.FAILED
            attempt.error_message = error_message
            attempt.completed_at = timezone.now()
            attempt.save(
                update_fields=[
                    "status",
                    "error_message",
                    "completed_at",
                ]
            )

            notification = Notification.objects.select_for_update().get(
                id=notification_id
            )

            notification.last_error = error_message

            if self.request.retries < self.max_retries:
                notification.status = NotificationStatus.RETRYING
            else:
                notification.status = NotificationStatus.FAILED

            notification.save(
                update_fields=[
                    "status",
                    "last_error",
                    "updated_at",
                ]
            )

        logger.exception(
            "Email delivery failed for notification %s. Attempt %s.",
            notification_id,
            attempt_number,
        )

        # Retry after 30 seconds, then after 2 minutes.
        retry_delays = [30, 120]

        if self.request.retries < self.max_retries:
            countdown = retry_delays[self.request.retries]

            raise self.retry(
                exc=exc,
                countdown=countdown,
            )

        return

    # Email was accepted by the configured email backend.
    with transaction.atomic():
        attempt.status = DeliveryStatus.SUCCESS
        attempt.completed_at = timezone.now()
        attempt.save(
            update_fields=[
                "status",
                "completed_at",
            ]
        )

        notification = Notification.objects.select_for_update().get(id=notification_id)

        notification.status = NotificationStatus.SENT
        notification.sent_at = timezone.now()
        notification.last_error = None
        notification.save(
            update_fields=[
                "status",
                "sent_at",
                "last_error",
                "updated_at",
            ]
        )

    logger.info(
        "Notification %s successfully sent to %s.",
        notification_id,
        recipient_email,
    )
