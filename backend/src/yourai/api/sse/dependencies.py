"""FastAPI dependencies for SSE endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING

from redis.asyncio import Redis

from yourai.core.config import settings

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

# Module-level connection pool — lazily initialised on first use.
_redis_pool: Redis | None = None


async def get_redis() -> AsyncGenerator[Redis, None]:
    """Yield a Redis client from the shared connection pool."""
    global _redis_pool  # noqa: PLW0603
    if _redis_pool is None:
        _redis_pool = Redis.from_url(
            settings.redis_url,
            decode_responses=False,
        )
    yield _redis_pool


async def close_redis() -> None:
    """Close the Redis connection pool. Called on app shutdown."""
    global _redis_pool  # noqa: PLW0603
    if _redis_pool is not None:
        await _redis_pool.aclose()
        _redis_pool = None
