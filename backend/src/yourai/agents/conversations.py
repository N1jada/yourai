"""Conversation service — CRUD for conversations table.

Every query filters by tenant_id AND user_id (users can only access their own conversations).
Implements soft delete via deleted_at timestamp.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID

import structlog
from sqlalchemy import func, select

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

from yourai.agents.models import Conversation
from yourai.agents.schemas import ConversationResponse, CreateConversation, UpdateConversation
from yourai.core.exceptions import NotFoundError
from yourai.core.schemas import Page

logger = structlog.get_logger()


class ConversationService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_conversation(
        self, conversation_id: UUID, tenant_id: UUID, user_id: UUID
    ) -> ConversationResponse:
        """Fetch a single conversation by ID. Raises 404 if not found or user doesn't own it."""
        result = await self._session.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.tenant_id == tenant_id,
                Conversation.user_id == user_id,
                Conversation.deleted_at.is_(None),  # Exclude soft-deleted
            )
        )
        conversation = result.scalar_one_or_none()
        if conversation is None:
            raise NotFoundError("Conversation not found.")
        return self._to_response(conversation)

    async def list_conversations(
        self, tenant_id: UUID, user_id: UUID, page: int = 1, page_size: int = 50
    ) -> Page[ConversationResponse]:
        """List conversations for a user with pagination. Excludes soft-deleted."""
        query = select(Conversation).where(
            Conversation.tenant_id == tenant_id,
            Conversation.user_id == user_id,
            Conversation.deleted_at.is_(None),
        )

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self._session.execute(count_query)
        total = total_result.scalar_one()

        # Paginate
        offset = (page - 1) * page_size
        query = query.order_by(Conversation.updated_at.desc()).offset(offset).limit(page_size)

        result = await self._session.execute(query)
        conversations = list(result.scalars().all())

        return Page(
            items=[self._to_response(c) for c in conversations],
            total=total,
            page=page,
            page_size=page_size,
            has_next=(offset + page_size) < total,
        )

    async def create_conversation(
        self, tenant_id: UUID, user_id: UUID, data: CreateConversation
    ) -> ConversationResponse:
        """Create a new conversation for a user."""
        conversation = Conversation(
            tenant_id=tenant_id,
            user_id=user_id,
            title=data.title,
            template_id=data.template_id,
        )
        self._session.add(conversation)
        await self._session.flush()
        await self._session.refresh(conversation)

        logger.info(
            "conversation_created",
            conversation_id=str(conversation.id),
            tenant_id=str(tenant_id),
            user_id=str(user_id),
        )
        return self._to_response(conversation)

    async def update_conversation(
        self, conversation_id: UUID, tenant_id: UUID, user_id: UUID, data: UpdateConversation
    ) -> ConversationResponse:
        """Update a conversation (rename, change state). User must own the conversation."""
        result = await self._session.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.tenant_id == tenant_id,
                Conversation.user_id == user_id,
                Conversation.deleted_at.is_(None),
            )
        )
        conversation = result.scalar_one_or_none()
        if conversation is None:
            raise NotFoundError("Conversation not found.")

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(conversation, field, value)

        await self._session.flush()
        await self._session.refresh(conversation)

        logger.info(
            "conversation_updated",
            conversation_id=str(conversation_id),
            tenant_id=str(tenant_id),
            user_id=str(user_id),
        )
        return self._to_response(conversation)

    async def delete_conversation(
        self, conversation_id: UUID, tenant_id: UUID, user_id: UUID
    ) -> None:
        """Soft delete a conversation (sets deleted_at timestamp). User must own it."""
        result = await self._session.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.tenant_id == tenant_id,
                Conversation.user_id == user_id,
                Conversation.deleted_at.is_(None),
            )
        )
        conversation = result.scalar_one_or_none()
        if conversation is None:
            raise NotFoundError("Conversation not found.")

        conversation.deleted_at = datetime.now(UTC)
        await self._session.flush()

        logger.info(
            "conversation_deleted",
            conversation_id=str(conversation_id),
            tenant_id=str(tenant_id),
            user_id=str(user_id),
        )

    @staticmethod
    def _to_response(conversation: Conversation) -> ConversationResponse:
        """Convert ORM model to Pydantic response.

        Manual construction avoids uuid_utils.UUID vs uuid.UUID issues (see MEMORY.md).
        """
        return ConversationResponse(
            id=UUID(str(conversation.id)),
            tenant_id=UUID(str(conversation.tenant_id)),
            user_id=UUID(str(conversation.user_id)),
            title=conversation.title,
            state=conversation.state,
            template_id=UUID(str(conversation.template_id)) if conversation.template_id else None,
            deleted_at=conversation.deleted_at,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
        )
