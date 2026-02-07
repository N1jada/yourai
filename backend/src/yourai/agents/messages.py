"""Message service — CRUD for messages table.

Every query filters by tenant_id. When accessing messages in a conversation,
verifies the conversation exists and belongs to the tenant.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

import structlog
from sqlalchemy import func, select

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

from yourai.agents.enums import MessageRole
from yourai.agents.models import Conversation, Message
from yourai.agents.schemas import MessageResponse, SendMessage
from yourai.core.exceptions import NotFoundError
from yourai.core.schemas import Page

logger = structlog.get_logger()


class MessageService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_messages(
        self, conversation_id: UUID, tenant_id: UUID, page: int = 1, page_size: int = 50
    ) -> Page[MessageResponse]:
        """List messages in a conversation with pagination.

        Verifies the conversation exists and belongs to the tenant.
        """
        # Verify conversation exists and belongs to tenant
        conv_result = await self._session.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.tenant_id == tenant_id,
                Conversation.deleted_at.is_(None),
            )
        )
        if conv_result.scalar_one_or_none() is None:
            raise NotFoundError("Conversation not found.")

        query = select(Message).where(
            Message.conversation_id == conversation_id,
            Message.tenant_id == tenant_id,
        )

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self._session.execute(count_query)
        total = total_result.scalar_one()

        # Paginate
        offset = (page - 1) * page_size
        query = query.order_by(Message.created_at.asc()).offset(offset).limit(page_size)

        result = await self._session.execute(query)
        messages = list(result.scalars().all())

        return Page(
            items=[self._to_response(m) for m in messages],
            total=total,
            page=page,
            page_size=page_size,
            has_next=(offset + page_size) < total,
        )

    async def create_message(
        self, conversation_id: UUID, tenant_id: UUID, data: SendMessage
    ) -> MessageResponse:
        """Create a new user message in a conversation.

        Verifies the conversation exists and belongs to the tenant.
        """
        # Verify conversation exists and belongs to tenant
        conv_result = await self._session.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.tenant_id == tenant_id,
                Conversation.deleted_at.is_(None),
            )
        )
        if conv_result.scalar_one_or_none() is None:
            raise NotFoundError("Conversation not found.")

        message = Message(
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            role=MessageRole.USER,
            content=data.content,
            file_attachments=data.file_attachments,
        )
        self._session.add(message)
        await self._session.flush()
        await self._session.refresh(message)

        logger.info(
            "message_created",
            message_id=str(message.id),
            conversation_id=str(conversation_id),
            tenant_id=str(tenant_id),
            role=MessageRole.USER,
        )
        return self._to_response(message)

    @staticmethod
    def _to_response(message: Message) -> MessageResponse:
        """Convert ORM model to Pydantic response.

        Manual construction avoids uuid_utils.UUID vs uuid.UUID issues (see MEMORY.md).
        """
        return MessageResponse(
            id=UUID(str(message.id)),
            tenant_id=UUID(str(message.tenant_id)),
            conversation_id=UUID(str(message.conversation_id)),
            request_id=UUID(str(message.request_id)) if message.request_id else None,
            role=message.role,
            content=message.content,
            state=message.state,
            metadata_=message.metadata_,
            file_attachments=message.file_attachments,
            confidence_level=message.confidence_level,
            verification_result=message.verification_result,
            created_at=message.created_at,
            updated_at=message.updated_at,
        )
