"""Conversation routes — CRUD for conversations and message sending.

This module handles:
- Conversation lifecycle (create, list, get, update, delete)
- Message listing
- Message sending (triggers agent invocation in background)
"""

from __future__ import annotations

import asyncio
from uuid import UUID

from anthropic import AsyncAnthropic
from fastapi import APIRouter, Depends, Query, Response, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from yourai.agents.conversations import ConversationService
from yourai.agents.invocation import AgentEngine
from yourai.agents.messages import MessageService
from yourai.agents.schemas import (
    ConversationResponse,
    CreateConversation,
    MessageResponse,
    SendMessage,
    UpdateConversation,
)
from yourai.api.sse.dependencies import get_redis
from yourai.core.config import settings
from yourai.core.database import get_db_session
from yourai.core.middleware import get_current_tenant, get_current_user
from yourai.core.schemas import Page, TenantConfig, UserResponse

router = APIRouter(prefix="/api/v1/conversations", tags=["conversations"])


@router.get("", response_model=Page[ConversationResponse])
async def list_conversations(
    tenant: TenantConfig = Depends(get_current_tenant),
    user: UserResponse = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
) -> Page[ConversationResponse]:
    """List user's conversations with pagination. Excludes soft-deleted."""
    service = ConversationService(session)
    return await service.list_conversations(tenant.id, user.id, page, page_size)


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    data: CreateConversation,
    tenant: TenantConfig = Depends(get_current_tenant),
    user: UserResponse = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ConversationResponse:
    """Create a new conversation for the current user."""
    service = ConversationService(session)
    result = await service.create_conversation(tenant.id, user.id, data)
    await session.commit()
    return result


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: UUID,
    tenant: TenantConfig = Depends(get_current_tenant),
    user: UserResponse = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ConversationResponse:
    """Get a single conversation by ID. User must own the conversation."""
    service = ConversationService(session)
    return await service.get_conversation(conversation_id, tenant.id, user.id)


@router.patch("/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: UUID,
    data: UpdateConversation,
    tenant: TenantConfig = Depends(get_current_tenant),
    user: UserResponse = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ConversationResponse:
    """Update a conversation (rename, change state). User must own it."""
    service = ConversationService(session)
    result = await service.update_conversation(conversation_id, tenant.id, user.id, data)
    await session.commit()
    return result


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: UUID,
    tenant: TenantConfig = Depends(get_current_tenant),
    user: UserResponse = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    """Soft delete a conversation (sets deleted_at timestamp). User must own it."""
    service = ConversationService(session)
    await service.delete_conversation(conversation_id, tenant.id, user.id)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{conversation_id}/messages", response_model=Page[MessageResponse])
async def list_messages(
    conversation_id: UUID,
    tenant: TenantConfig = Depends(get_current_tenant),
    user: UserResponse = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
) -> Page[MessageResponse]:
    """List messages in a conversation with pagination.

    Note: This endpoint doesn't enforce user ownership check on the conversation.
    The MessageService will verify the conversation exists and belongs to the tenant.
    For stricter isolation, you could add a conversation ownership check here.
    """
    service = MessageService(session)
    return await service.list_messages(conversation_id, tenant.id, page, page_size)


@router.post(
    "/{conversation_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def send_message(
    conversation_id: UUID,
    data: SendMessage,
    tenant: TenantConfig = Depends(get_current_tenant),
    user: UserResponse = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),
) -> MessageResponse:
    """Send a message in a conversation. Triggers agent invocation in background.

    Flow:
    1. Creates user message in DB immediately
    2. Returns user message to client
    3. Triggers agent invocation in background (async task)
    4. Client should listen on SSE stream (GET /api/v1/sse/conversation/{id})
       to receive the assistant's response

    The agent invocation will:
    - Classify the query (Router agent)
    - Generate streaming response (Orchestrator agent)
    - Emit SSE events: AgentStartEvent, ContentDeltaEvent, AgentCompleteEvent, MessageCompleteEvent
    - Create assistant message in DB

    Returns:
        The user's message (not the assistant's response)
    """
    # Create user message
    msg_service = MessageService(session)
    user_msg = await msg_service.create_message(conversation_id, tenant.id, data)
    await session.commit()

    # Trigger agent invocation in background
    # NOTE: In production, this should be a Celery task for reliability and retry logic.
    # For Session 1, we use asyncio.create_task() for simplicity.
    # The task gets a new DB session to avoid transaction conflicts.
    async def run_agent() -> None:
        """Background task to run agent invocation with its own DB session."""
        # Import here to avoid circular dependency
        from yourai.core.database import get_async_session_maker

        session_maker = get_async_session_maker()
        async with session_maker() as agent_session:
            engine = AgentEngine(
                agent_session,
                redis,
                AsyncAnthropic(api_key=settings.anthropic_api_key),
            )
            try:
                await engine.invoke(
                    data.content,
                    conversation_id,
                    tenant.id,
                    user.id,
                    data.persona_id,
                )
            except Exception:
                # Errors are already logged in AgentEngine.invoke()
                # We don't re-raise here to avoid breaking the background task
                pass

    asyncio.create_task(run_agent())

    return user_msg
