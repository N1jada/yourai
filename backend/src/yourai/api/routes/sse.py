"""SSE streaming endpoints.

Endpoints:
    GET /api/v1/conversations/{id}/stream   — Conversation event stream
    GET /api/v1/policy-reviews/{id}/stream  — Policy review event stream
    GET /api/v1/users/me/events             — User-level push events
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated
from uuid import UUID  # noqa: TCH003 — FastAPI needs UUID at runtime for path params

import structlog
from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import StreamingResponse

from yourai.api.sse.auth import verify_sse_token
from yourai.api.sse.channels import SSEChannel
from yourai.api.sse.dependencies import get_redis
from yourai.api.sse.manager import event_stream

if TYPE_CHECKING:
    from redis.asyncio import Redis

logger = structlog.get_logger()

router = APIRouter()

RedisDep = Annotated["Redis", Depends(get_redis)]
LastEventId = Annotated[str | None, Header(alias="Last-Event-ID")]


@router.get("/api/v1/conversations/{conversation_id}/stream")
async def conversation_stream(
    conversation_id: UUID,
    request: Request,
    redis: RedisDep,
    last_event_id: LastEventId = None,
) -> StreamingResponse:
    """SSE stream for conversation events (agent lifecycle, content, sources)."""
    claims = await verify_sse_token(request)
    tenant_id = claims.tenant_id
    user_id = claims.user_id

    logger.info(
        "sse_conversation_stream_requested",
        tenant_id=str(tenant_id),
        user_id=str(user_id),
        conversation_id=str(conversation_id),
    )

    channel = SSEChannel.for_conversation(tenant_id, conversation_id)

    return StreamingResponse(
        event_stream(redis, channel, last_event_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/api/v1/policy-reviews/{review_id}/stream")
async def policy_review_stream(
    review_id: UUID,
    request: Request,
    redis: RedisDep,
    last_event_id: LastEventId = None,
) -> StreamingResponse:
    """SSE stream for policy review progress events."""
    claims = await verify_sse_token(request)
    tenant_id = claims.tenant_id
    user_id = claims.user_id

    logger.info(
        "sse_policy_review_stream_requested",
        tenant_id=str(tenant_id),
        user_id=str(user_id),
        review_id=str(review_id),
    )

    channel = SSEChannel.for_policy_review(tenant_id, review_id)

    return StreamingResponse(
        event_stream(redis, channel, last_event_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/api/v1/users/me/events")
async def user_events(
    request: Request,
    redis: RedisDep,
    last_event_id: LastEventId = None,
) -> StreamingResponse:
    """SSE stream for user-level push events (title updates, alerts, etc.)."""
    claims = await verify_sse_token(request)
    tenant_id = claims.tenant_id
    user_id = claims.user_id

    logger.info(
        "sse_user_events_requested",
        tenant_id=str(tenant_id),
        user_id=str(user_id),
    )

    channel = SSEChannel.for_user(tenant_id, user_id)

    return StreamingResponse(
        event_stream(redis, channel, last_event_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
