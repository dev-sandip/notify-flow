
import json
import logging

from confluent_kafka import KafkaException, Producer
from django.conf import settings

logger = logging.getLogger(__name__)

_producer = None


def get_kafka_producer() -> Producer:
    """Return a reusable Kafka producer instance."""

    global _producer

    if _producer is None:
        _producer = Producer(
            {
                "bootstrap.servers": settings.KAFKA_BOOTSTRAP_SERVERS,
                "client.id": "notifyflow-outbox-publisher",
                "acks": "all",
                "enable.idempotence": True,
                "retries": 10,
                "max.in.flight.requests.per.connection": 5,
                "compression.type": "snappy",
                "linger.ms": 10,
            }
        )

    return _producer


def publish_outbox_event(event):
    """
    Publish an OutboxEvent to Kafka.

    Returns only after Kafka acknowledges the message.
    Raises an exception if delivery fails or times out.
    """

    producer = get_kafka_producer()

    message = {
        "event_id": str(event.id),
        "event_type": event.event_type,
        "aggregate_type": event.aggregate_type,
        "aggregate_id": str(event.aggregate_id),
        "schema_version": event.schema_version,
        "occurred_at": event.occurred_at.isoformat(),
        "created_at": event.created_at.isoformat(),
        "payload": event.payload,
    }

    delivery_result = {}

    def delivery_callback(error, kafka_message):
        delivery_result["error"] = error

        if error is None:
            delivery_result["topic"] = kafka_message.topic()
            delivery_result["partition"] = kafka_message.partition()
            delivery_result["offset"] = kafka_message.offset()

    try:
        producer.produce(
            topic=settings.KAFKA_NOTIFICATION_TOPIC,
            key=str(event.aggregate_id),
            value=json.dumps(message),
            on_delivery=delivery_callback,
        )

        remaining = producer.flush(timeout=10)

        if remaining > 0:
            raise TimeoutError(
                f"Kafka delivery timed out for event {event.id}."
            )

        if "error" not in delivery_result:
            raise RuntimeError(
                f"No Kafka delivery confirmation received for event {event.id}."
            )

        if delivery_result["error"] is not None:
            raise KafkaException(delivery_result["error"])

        logger.info(
            "Published event %s to %s partition %s offset %s",
            event.id,
            delivery_result["topic"],
            delivery_result["partition"],
            delivery_result["offset"],
        )

    except Exception:
        logger.exception(
            "Kafka publishing failed for event %s.",
            event.id,
        )
        raise
