"""Tests for SSE endpoint authentication and streaming.

Uses FastAPI TestClient with httpx and fakeredis.
The streaming tests use the event_stream generator directly to avoid
hanging on the infinite SSE loop in httpx ASGI transport.
"""

from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest
from fakeredis.aioredis import FakeRedis
from httpx import ASGITransport, AsyncClient

from yourai.api.sse.auth import SSETokenClaims
from yourai.api.sse.channels import SSEChannel
from yourai.api.sse.events import ContentDeltaEvent, ConversationTitleUpdatedEvent
from yourai.api.sse.manager import event_stream
from yourai.api.sse.publisher import EventPublisher


@pytest.fixture
def tenant_id():
    return uuid4()


@pytest.fixture
def user_id():
    return uuid4()


@pytest.fixture
def claims(tenant_id, user_id):
    return SSETokenClaims(sub=str(user_id), user_id=user_id, tenant_id=tenant_id)


@pytest.fixture
def fake_redis():
    return FakeRedis()


@pytest.fixture
def app():
    """Create a fresh FastAPI app (no dependency overrides for auth tests)."""
    from yourai.api.main import create_app

    return create_app()


# ---------------------------------------------------------------------------
# Authentication tests — verify 401 without valid token
# ---------------------------------------------------------------------------


async def test_conversation_stream_requires_auth(app) -> None:
    """Requests without a valid token should get 401."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/v1/conversations/{uuid4()}/stream")
        assert response.status_code == 401


async def test_policy_review_stream_requires_auth(app) -> None:
    """Requests without a valid token should get 401."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/v1/policy-reviews/{uuid4()}/stream")
        assert response.status_code == 401


async def test_user_events_requires_auth(app) -> None:
    """Requests without a valid token should get 401."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/users/me/events")
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Streaming tests — use event_stream generator directly to avoid ASGI hangs
# ---------------------------------------------------------------------------


async def test_publish_event_received_by_stream(fake_redis, tenant_id) -> None:
    """Publish an event, then verify the event_stream generator yields it."""
    conv_id = uuid4()
    channel = SSEChannel.for_conversation(tenant_id, conv_id)
    publisher = EventPublisher(fake_redis)  # type: ignore[arg-type]

    collected: list[str] = []

    async def consume():
        async for frame in event_stream(fake_redis, channel):  # type: ignore[arg-type]
            collected.append(frame)
            # Stop after we receive a data frame (not heartbeat)
            if "data:" in frame:
                break

    consumer_task = asyncio.create_task(consume())

    # Give subscriber time to connect
    await asyncio.sleep(0.1)

    # Publish
    await publisher.publish(channel, ContentDeltaEvent(text="streamed text"))

    try:
        await asyncio.wait_for(consumer_task, timeout=5.0)
    except TimeoutError:
        consumer_task.cancel()
        try:
            await consumer_task
        except asyncio.CancelledError:
            pass

    data_frames = [f for f in collected if "data:" in f]
    assert len(data_frames) >= 1
    assert "streamed text" in data_frames[0]


async def test_reconnection_replays_missed_events(fake_redis, tenant_id) -> None:
    """When reconnecting with Last-Event-ID, missed events are replayed."""
    conv_id = uuid4()
    channel = SSEChannel.for_conversation(tenant_id, conv_id)
    publisher = EventPublisher(fake_redis)  # type: ignore[arg-type]

    # Publish 3 events while no subscriber is connected
    id1 = await publisher.publish(channel, ContentDeltaEvent(text="event-one"))
    id2 = await publisher.publish(channel, ContentDeltaEvent(text="event-two"))
    id3 = await publisher.publish(channel, ContentDeltaEvent(text="event-three"))

    # Reconnect with Last-Event-ID = id1 → should replay event-two and event-three
    collected: list[str] = []
    replay_count = 0

    async def consume():
        nonlocal replay_count
        async for frame in event_stream(fake_redis, channel, last_event_id=id1):  # type: ignore[arg-type]
            collected.append(frame)
            if "data:" in frame:
                replay_count += 1
            # We expect 2 replayed events — stop after collecting them
            if replay_count >= 2:
                break

    consumer_task = asyncio.create_task(consume())

    try:
        await asyncio.wait_for(consumer_task, timeout=5.0)
    except TimeoutError:
        consumer_task.cancel()
        try:
            await consumer_task
        except asyncio.CancelledError:
            pass

    data_frames = [f for f in collected if "data:" in f]
    assert len(data_frames) == 2
    assert "event-two" in data_frames[0]
    assert "event-three" in data_frames[1]


async def test_cross_tenant_event_isolation_stream(fake_redis) -> None:
    """Events published to tenant A must not appear on tenant B's stream."""
    tenant_a = uuid4()
    tenant_b = uuid4()
    resource = uuid4()

    ch_a = SSEChannel.for_conversation(tenant_a, resource)
    ch_b = SSEChannel.for_conversation(tenant_b, resource)
    publisher = EventPublisher(fake_redis)  # type: ignore[arg-type]

    collected_b: list[str] = []

    async def consume_b():
        async for frame in event_stream(fake_redis, ch_b):  # type: ignore[arg-type]
            collected_b.append(frame)
            if "data:" in frame:
                break

    consumer_task = asyncio.create_task(consume_b())
    await asyncio.sleep(0.1)

    # Publish to tenant A only
    await publisher.publish(ch_a, ContentDeltaEvent(text="secret A data"))

    # Wait briefly — tenant B should NOT receive anything
    await asyncio.sleep(0.5)
    consumer_task.cancel()
    try:
        await consumer_task
    except asyncio.CancelledError:
        pass

    data_frames = [f for f in collected_b if "data:" in f]
    assert len(data_frames) == 0, "Tenant B should not receive tenant A's events"


async def test_user_push_event_stream(fake_redis, tenant_id) -> None:
    """User push events should be delivered via the user channel."""
    user_id = uuid4()
    channel = SSEChannel.for_user(tenant_id, user_id)
    publisher = EventPublisher(fake_redis)  # type: ignore[arg-type]

    collected: list[str] = []

    async def consume():
        async for frame in event_stream(fake_redis, channel):  # type: ignore[arg-type]
            collected.append(frame)
            if "data:" in frame:
                break

    consumer_task = asyncio.create_task(consume())
    await asyncio.sleep(0.1)

    await publisher.publish(
        channel,
        ConversationTitleUpdatedEvent(
            conversation_id=str(uuid4()),
            title="New title",
        ),
    )

    try:
        await asyncio.wait_for(consumer_task, timeout=5.0)
    except TimeoutError:
        consumer_task.cancel()
        try:
            await consumer_task
        except asyncio.CancelledError:
            pass

    data_frames = [f for f in collected if "data:" in f]
    assert len(data_frames) >= 1
    assert "New title" in data_frames[0]


async def test_sse_frame_format(fake_redis, tenant_id) -> None:
    """Verify SSE frames have correct id, event, and data fields."""
    conv_id = uuid4()
    channel = SSEChannel.for_conversation(tenant_id, conv_id)
    publisher = EventPublisher(fake_redis)  # type: ignore[arg-type]

    collected: list[str] = []

    async def consume():
        async for frame in event_stream(fake_redis, channel):  # type: ignore[arg-type]
            collected.append(frame)
            if "data:" in frame:
                break

    consumer_task = asyncio.create_task(consume())
    await asyncio.sleep(0.1)

    await publisher.publish(channel, ContentDeltaEvent(text="hello"))

    try:
        await asyncio.wait_for(consumer_task, timeout=5.0)
    except TimeoutError:
        consumer_task.cancel()
        try:
            await consumer_task
        except asyncio.CancelledError:
            pass

    assert len(collected) >= 1
    frame = collected[0]

    # SSE frame should contain id:, event:, data: fields
    assert "id: " in frame
    assert "event: content_delta" in frame
    assert "data: " in frame
    assert '"text":"hello"' in frame or '"text": "hello"' in frame
