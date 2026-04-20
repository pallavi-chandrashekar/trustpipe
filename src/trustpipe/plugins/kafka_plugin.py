"""Kafka plugin — tracks messages flowing through Kafka topics.

Requires: pip install confluent-kafka

Usage:
    from trustpipe import TrustPipe
    from trustpipe.plugins.kafka_plugin import KafkaPlugin

    tp = TrustPipe()
    kafka = KafkaPlugin(tp)

    # Wrap a consumer
    tracked_consumer = kafka.wrap_consumer(consumer)
    msg = tracked_consumer.poll(1.0)  # auto-tracked

    # Wrap a producer
    tracked_producer = kafka.wrap_producer(producer)
    tracked_producer.produce("topic", value=data)  # auto-tracked
"""

from __future__ import annotations

import contextlib
import hashlib
from typing import Any

from trustpipe.core.engine import TrustPipe


class KafkaPlugin:
    """Tracks Kafka consumer/producer operations as provenance records."""

    def __init__(self, tp: TrustPipe) -> None:
        self._tp = tp

    def wrap_consumer(self, consumer: Any) -> TrackedConsumer:
        """Wrap a confluent_kafka.Consumer with provenance tracking."""
        return TrackedConsumer(consumer, self._tp)

    def wrap_producer(self, producer: Any) -> TrackedProducer:
        """Wrap a confluent_kafka.Producer with provenance tracking."""
        return TrackedProducer(producer, self._tp)


class TrackedConsumer:
    """Wrapper around confluent_kafka.Consumer that auto-tracks consumed messages."""

    def __init__(self, consumer: Any, tp: TrustPipe) -> None:
        self._consumer = consumer
        self._tp = tp
        self._batch_count: dict[str, int] = {}  # topic -> count

    def poll(self, timeout: float = 1.0) -> Any:
        msg = self._consumer.poll(timeout)
        if msg is not None and not msg.error():
            topic = msg.topic()
            self._batch_count[topic] = self._batch_count.get(topic, 0) + 1

            # Track every N messages or on first message per topic
            if self._batch_count[topic] == 1 or self._batch_count[topic] % 1000 == 0:
                try:
                    value = msg.value()
                    hashlib.sha256(
                        value if isinstance(value, bytes) else str(value).encode()
                    ).hexdigest()
                    self._tp.track(
                        {
                            "row_count": self._batch_count[topic],
                            "message_size": len(value) if value else 0,
                        },
                        name=f"kafka:{topic}",
                        source=f"kafka://{topic}/{msg.partition()}/{msg.offset()}",
                        tags=["kafka", "consumer"],
                        metadata={
                            "topic": topic,
                            "partition": msg.partition(),
                            "offset": msg.offset(),
                            "batch_count": self._batch_count[topic],
                        },
                    )
                except Exception:
                    pass  # never break the consumer
        return msg

    def subscribe(self, topics: list[str], **kwargs: Any) -> None:
        self._consumer.subscribe(topics, **kwargs)

    def close(self) -> None:
        # Track final batch counts before closing
        for topic, count in self._batch_count.items():
            with contextlib.suppress(Exception):
                self._tp.track(
                    {"row_count": count},
                    name=f"kafka:{topic}",
                    source=f"kafka://{topic}/final",
                    tags=["kafka", "consumer", "session-end"],
                    metadata={"topic": topic, "total_consumed": count},
                )
        self._consumer.close()

    def __getattr__(self, name: str) -> Any:
        return getattr(self._consumer, name)


class TrackedProducer:
    """Wrapper around confluent_kafka.Producer that auto-tracks produced messages."""

    def __init__(self, producer: Any, tp: TrustPipe) -> None:
        self._producer = producer
        self._tp = tp
        self._batch_count: dict[str, int] = {}

    def produce(self, topic: str, value: Any = None, key: Any = None, **kwargs: Any) -> None:
        self._producer.produce(topic, value=value, key=key, **kwargs)
        self._batch_count[topic] = self._batch_count.get(topic, 0) + 1

        if self._batch_count[topic] == 1 or self._batch_count[topic] % 1000 == 0:
            try:
                size = len(value) if value else 0
                self._tp.track(
                    {"row_count": self._batch_count[topic], "message_size": size},
                    name=f"kafka:{topic}",
                    source=f"kafka://{topic}/produced",
                    tags=["kafka", "producer"],
                    metadata={
                        "topic": topic,
                        "batch_count": self._batch_count[topic],
                    },
                )
            except Exception:
                pass

    def flush(self, timeout: float = -1) -> int:
        return self._producer.flush(timeout)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._producer, name)
