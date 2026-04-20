"""Tests for Kafka plugin — uses mock consumer/producer."""

from unittest.mock import MagicMock

from trustpipe.plugins.kafka_plugin import KafkaPlugin, TrackedConsumer, TrackedProducer


def test_tracked_consumer_wraps_poll(tp):
    """TrackedConsumer should pass through poll and track messages."""
    mock_consumer = MagicMock()
    mock_msg = MagicMock()
    mock_msg.error.return_value = None
    mock_msg.topic.return_value = "test-topic"
    mock_msg.partition.return_value = 0
    mock_msg.offset.return_value = 42
    mock_msg.value.return_value = b'{"key": "value"}'
    mock_consumer.poll.return_value = mock_msg

    kafka = KafkaPlugin(tp)
    tracked = kafka.wrap_consumer(mock_consumer)
    result = tracked.poll(1.0)

    assert result == mock_msg
    mock_consumer.poll.assert_called_once_with(1.0)

    # Should have tracked the message
    chain = tp.trace("kafka:test-topic")
    assert len(chain) >= 1


def test_tracked_consumer_handles_none(tp):
    """TrackedConsumer should handle None messages (timeout)."""
    mock_consumer = MagicMock()
    mock_consumer.poll.return_value = None

    tracked = TrackedConsumer(mock_consumer, tp)
    result = tracked.poll(1.0)

    assert result is None
    chain = tp.trace("kafka:test-topic")
    assert len(chain) == 0  # nothing tracked


def test_tracked_producer_wraps_produce(tp):
    """TrackedProducer should pass through produce and track messages."""
    mock_producer = MagicMock()

    kafka = KafkaPlugin(tp)
    tracked = kafka.wrap_producer(mock_producer)
    tracked.produce("output-topic", value=b"hello world")

    mock_producer.produce.assert_called_once_with("output-topic", value=b"hello world", key=None)

    chain = tp.trace("kafka:output-topic")
    assert len(chain) >= 1


def test_tracked_consumer_subscribe_passthrough(tp):
    """subscribe() should pass through to underlying consumer."""
    mock_consumer = MagicMock()
    tracked = TrackedConsumer(mock_consumer, tp)
    tracked.subscribe(["topic1", "topic2"])
    mock_consumer.subscribe.assert_called_once_with(["topic1", "topic2"])


def test_tracked_producer_flush_passthrough(tp):
    """flush() should pass through to underlying producer."""
    mock_producer = MagicMock()
    mock_producer.flush.return_value = 0
    tracked = TrackedProducer(mock_producer, tp)
    result = tracked.flush(5.0)
    mock_producer.flush.assert_called_once_with(5.0)
    assert result == 0
