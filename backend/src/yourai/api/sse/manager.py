"""SSE connection manager — subscribes to Redis pub/sub and streams to clients.

Handles:
- Redis pub/sub subscription per channel
- Heartbeat keep-alive (``:``)
- Reconnection replay via ``Last-Event-ID``
- Graceful disconnection cleanup
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import structlog

from yourai.api.sse.publisher import EventPublisher
from yourai.core.config import settings

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from redis.asyncio import Redis

    from yourai.api.sse.channels import SSEChannel

logger = structlog.get_logger()


def _format_sse(event_id: str, event_type: str, data: str) -> str:
    """Format a single SSE frame.

    Note: We intentionally omit the ``event:`` line so that all events are
    dispatched to the browser's ``EventSource.onmessage`` handler.  The
    event type is already inside the JSON payload (``event_type`` field),
    which the frontend uses for routing.
    """
    return f"id: {event_id}\ndata: {data}\n\n"


async def event_stream(
    redis: Redis,
    channel: SSEChannel,
    last_event_id: str | None = None,
) -> AsyncGenerator[str, None]:
    """Async generator that yields SSE-formatted strings.

    1. Replays missed events if ``last_event_id`` is set.
    2. Subscribes to Redis pub/sub and yields live events.
    3. Sends heartbeat comments at regular intervals.

    The caller (FastAPI StreamingResponse) iterates this generator.
    """
    publisher = EventPublisher(redis)
    heartbeat_interval = settings.sse_heartbeat_interval_seconds

    # --- Phase 1: Replay missed events ---
    if last_event_id is not None:
        replay_events = await publisher.get_replay_events(channel, last_event_id)
        for event_id, event_type, payload in replay_events:
            yield _format_sse(event_id, event_type, payload)

    # --- Phase 2: Live subscription ---
    pubsub = redis.pubsub()
    await pubsub.subscribe(channel.pubsub_key)

    logger.info(
        "sse_client_connected",
        channel=channel.pubsub_key,
        tenant_id=str(channel.tenant_id),
    )

    try:
        while True:
            try:
                message = await asyncio.wait_for(
                    pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0),
                    timeout=heartbeat_interval,
                )
            except TimeoutError:
                # Send heartbeat comment to keep the connection alive
                yield ": heartbeat\n\n"
                continue

            if message is None:
                # No message within the inner timeout — loop and try again
                # (the outer wait_for handles heartbeats)
                continue

            if message["type"] != "message":
                continue

            raw = message["data"]
            wire = raw.decode() if isinstance(raw, bytes) else raw
            parts = wire.split("\n", 2)
            if len(parts) != 3:
                continue

            event_id, event_type, payload = parts
            yield _format_sse(event_id, event_type, payload)

    except asyncio.CancelledError:
        logger.info(
            "sse_client_disconnected",
            channel=channel.pubsub_key,
            tenant_id=str(channel.tenant_id),
        )
    finally:
        await pubsub.unsubscribe(channel.pubsub_key)
        await pubsub.close()
