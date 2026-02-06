"""Event publisher — writes events to Redis pub/sub and the replay buffer.

Other services (Celery tasks, API endpoints, agent engine) use this module
to push typed events. The SSE connection manager subscribes and streams
them to connected clients.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import structlog

from yourai.core.config import settings

if TYPE_CHECKING:
    from redis.asyncio import Redis

    from yourai.api.sse.channels import SSEChannel
    from yourai.api.sse.events import AnySSEEvent

logger = structlog.get_logger()

# Monotonic counter appended to timestamp to guarantee ordering within a ms.
_sequence: int = 0


def _generate_event_id() -> str:
    """Generate a monotonically increasing event ID.

    Format: ``<unix_millis>-<seq>``  — compatible with ``Last-Event-ID`` header.
    """
    global _sequence  # noqa: PLW0603
    now_ms = int(time.time() * 1000)
    _sequence += 1
    return f"{now_ms}-{_sequence}"


class EventPublisher:
    """Publishes SSE events to Redis pub/sub with replay buffer support."""

    def __init__(self, redis: Redis) -> None:
        self._redis = redis
        self._replay_window = settings.sse_replay_window_seconds

    async def publish(self, channel: SSEChannel, event: AnySSEEvent) -> str:
        """Publish an event to the given channel.

        1. Serialises the event with an ``event_id``.
        2. Stores in the replay sorted set (score = timestamp).
        3. Publishes to Redis pub/sub so live subscribers receive it.

        Returns the generated ``event_id``.
        """
        event_id = _generate_event_id()
        payload = event.model_dump_json()

        # The wire format stored in both replay and pub/sub is:
        #   <event_id>\n<event_type>\n<json_payload>
        wire = f"{event_id}\n{event.event_type}\n{payload}"

        pipe = self._redis.pipeline(transaction=False)

        # Store in replay buffer (sorted set, score = current time)
        pipe.zadd(channel.replay_key, {wire: time.time()})

        # Trim events older than the replay window
        cutoff = time.time() - self._replay_window
        pipe.zremrangebyscore(channel.replay_key, "-inf", cutoff)

        # Set TTL on the replay key so it auto-expires if unused
        pipe.expire(channel.replay_key, self._replay_window * 2)

        # Publish to live subscribers
        pipe.publish(channel.pubsub_key, wire)

        await pipe.execute()

        logger.debug(
            "sse_event_published",
            channel=channel.pubsub_key,
            event_type=event.event_type,
            event_id=event_id,
            tenant_id=str(channel.tenant_id),
        )

        return event_id

    async def get_replay_events(
        self,
        channel: SSEChannel,
        last_event_id: str | None = None,
    ) -> list[tuple[str, str, str]]:
        """Retrieve events from the replay buffer for reconnection.

        If ``last_event_id`` is provided, returns only events *after* that ID.
        Otherwise returns all events within the replay window.

        Returns a list of ``(event_id, event_type, json_payload)`` tuples,
        ordered chronologically.
        """
        # Trim stale entries first
        cutoff = time.time() - self._replay_window
        await self._redis.zremrangebyscore(channel.replay_key, "-inf", cutoff)

        # Fetch all remaining replay entries
        raw_entries: list[bytes | str] = await self._redis.zrangebyscore(
            channel.replay_key, "-inf", "+inf"
        )

        events: list[tuple[str, str, str]] = []
        past_last = last_event_id is None

        for entry in raw_entries:
            wire = entry.decode() if isinstance(entry, bytes) else entry
            parts = wire.split("\n", 2)
            if len(parts) != 3:
                continue
            eid, etype, payload = parts

            if not past_last:
                if eid == last_event_id:
                    past_last = True
                continue

            events.append((eid, etype, payload))

        return events
