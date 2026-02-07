"""SSE streaming helpers for agent events.

Convenience wrappers around EventPublisher for emitting agent lifecycle events.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from redis.asyncio import Redis

    from yourai.api.sse.channels import SSEChannel
    from yourai.api.sse.events import AnySSEEvent

from yourai.api.sse.publisher import EventPublisher


async def emit_agent_event(
    redis: Redis,
    channel: SSEChannel,
    event: AnySSEEvent,
) -> str:
    """Convenience wrapper for publishing agent events to SSE.

    Args:
        redis: Redis client for pub/sub
        channel: SSE channel to publish to
        event: Typed SSE event to publish

    Returns:
        Generated event_id
    """
    publisher = EventPublisher(redis)
    return await publisher.publish(channel, event)
