"""Tests for EventPublisher — publish, replay, and cross-tenant isolation.

Uses fakeredis for a self-contained in-memory Redis that supports pub/sub.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from fakeredis.aioredis import FakeRedis

from yourai.api.sse.channels import SSEChannel
from yourai.api.sse.events import ContentDeltaEvent, ErrorEvent
from yourai.api.sse.publisher import EventPublisher


@pytest.fixture
async def redis() -> FakeRedis:
    return FakeRedis()


@pytest.fixture
def tenant_id():
    return uuid4()


@pytest.fixture
def publisher(redis: FakeRedis) -> EventPublisher:
    return EventPublisher(redis)  # type: ignore[arg-type]


async def test_publish_stores_in_replay_buffer(
    publisher: EventPublisher, redis: FakeRedis, tenant_id
) -> None:
    """Published events should appear in the replay sorted set."""
    channel = SSEChannel.for_conversation(tenant_id, uuid4())
    event = ContentDeltaEvent(text="Hello")

    event_id = await publisher.publish(channel, event)

    assert event_id  # non-empty string
    entries = await redis.zrangebyscore(channel.replay_key, "-inf", "+inf")
    assert len(entries) == 1

    wire = entries[0].decode()
    assert event_id in wire
    assert "content_delta" in wire
    assert "Hello" in wire


async def test_publish_notifies_subscribers(
    publisher: EventPublisher, redis: FakeRedis, tenant_id
) -> None:
    """A subscriber on the pub/sub channel should receive the published event."""
    channel = SSEChannel.for_conversation(tenant_id, uuid4())
    pubsub = redis.pubsub()
    await pubsub.subscribe(channel.pubsub_key)

    # Drain the subscribe confirmation message
    msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=0.5)

    event = ContentDeltaEvent(text="World")
    await publisher.publish(channel, event)

    msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
    assert msg is not None
    assert msg["type"] == "message"

    wire = msg["data"].decode() if isinstance(msg["data"], bytes) else msg["data"]
    assert "content_delta" in wire
    assert "World" in wire

    await pubsub.unsubscribe(channel.pubsub_key)
    await pubsub.close()


async def test_replay_returns_events_after_last_event_id(
    publisher: EventPublisher, tenant_id
) -> None:
    """Replay should only return events after the given Last-Event-ID."""
    channel = SSEChannel.for_conversation(tenant_id, uuid4())

    id1 = await publisher.publish(channel, ContentDeltaEvent(text="one"))
    id2 = await publisher.publish(channel, ContentDeltaEvent(text="two"))
    id3 = await publisher.publish(channel, ContentDeltaEvent(text="three"))

    # Ask for events after id1 — should get id2 and id3
    events = await publisher.get_replay_events(channel, last_event_id=id1)
    assert len(events) == 2
    assert events[0][0] == id2
    assert events[1][0] == id3


async def test_replay_returns_all_when_no_last_event_id(
    publisher: EventPublisher, tenant_id
) -> None:
    """Without Last-Event-ID, replay should return all events in the window."""
    channel = SSEChannel.for_conversation(tenant_id, uuid4())

    await publisher.publish(channel, ContentDeltaEvent(text="a"))
    await publisher.publish(channel, ContentDeltaEvent(text="b"))

    events = await publisher.get_replay_events(channel, last_event_id=None)
    assert len(events) == 2


async def test_cross_tenant_isolation(publisher: EventPublisher) -> None:
    """Events published to tenant A's channel must not appear in tenant B's."""
    tenant_a = uuid4()
    tenant_b = uuid4()
    resource = uuid4()

    ch_a = SSEChannel.for_conversation(tenant_a, resource)
    ch_b = SSEChannel.for_conversation(tenant_b, resource)

    await publisher.publish(ch_a, ContentDeltaEvent(text="tenant A data"))

    # Tenant B's replay buffer should be empty
    events_b = await publisher.get_replay_events(ch_b)
    assert len(events_b) == 0

    # Tenant A's should have the event
    events_a = await publisher.get_replay_events(ch_a)
    assert len(events_a) == 1
    assert "tenant A data" in events_a[0][2]


async def test_cross_tenant_pubsub_isolation(redis: FakeRedis) -> None:
    """Pub/sub subscribers on different tenant channels should not cross-receive."""
    publisher = EventPublisher(redis)  # type: ignore[arg-type]
    tenant_a = uuid4()
    tenant_b = uuid4()
    resource = uuid4()

    ch_a = SSEChannel.for_conversation(tenant_a, resource)
    ch_b = SSEChannel.for_conversation(tenant_b, resource)

    sub_b = redis.pubsub()
    await sub_b.subscribe(ch_b.pubsub_key)
    # Drain subscribe confirmation
    await sub_b.get_message(ignore_subscribe_messages=True, timeout=0.5)

    # Publish to tenant A
    await publisher.publish(ch_a, ContentDeltaEvent(text="secret"))

    # Subscriber on tenant B should get nothing
    msg = await sub_b.get_message(ignore_subscribe_messages=True, timeout=0.5)
    assert msg is None

    await sub_b.unsubscribe(ch_b.pubsub_key)
    await sub_b.close()


async def test_multiple_event_types_in_replay(publisher: EventPublisher, tenant_id) -> None:
    """Different event types should all appear in the replay buffer correctly."""
    channel = SSEChannel.for_conversation(tenant_id, uuid4())

    await publisher.publish(channel, ContentDeltaEvent(text="hello"))
    await publisher.publish(
        channel,
        ErrorEvent(code="upstream_error", message="fail", recoverable=True),
    )

    events = await publisher.get_replay_events(channel)
    assert len(events) == 2
    assert events[0][1] == "content_delta"
    assert events[1][1] == "error"
