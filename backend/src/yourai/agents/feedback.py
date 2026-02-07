"""Feedback service — submit and query feedback on messages.

Every query filters by tenant_id at the application level.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

import structlog
from sqlalchemy import select

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

from yourai.agents.models import Feedback, Message
from yourai.agents.schemas import CreateFeedback, FeedbackResponse
from yourai.core.exceptions import NotFoundError

logger = structlog.get_logger()


class FeedbackService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def submit_feedback(
        self,
        message_id: UUID,
        user_id: UUID,
        tenant_id: UUID,
        data: CreateFeedback,
    ) -> FeedbackResponse:
        """Submit or update feedback on a message (upsert pattern)."""
        # Verify message exists and belongs to tenant
        msg_result = await self._session.execute(
            select(Message).where(
                Message.id == message_id,
                Message.tenant_id == tenant_id,
            )
        )
        if msg_result.scalar_one_or_none() is None:
            raise NotFoundError("Message not found.")

        # Check for existing feedback
        existing_result = await self._session.execute(
            select(Feedback).where(
                Feedback.message_id == message_id,
                Feedback.user_id == user_id,
                Feedback.tenant_id == tenant_id,
            )
        )
        feedback = existing_result.scalar_one_or_none()

        if feedback is not None:
            # Update existing feedback
            feedback.rating = data.rating
            if data.comment is not None:
                feedback.comment = data.comment
            self._session.add(feedback)
            await self._session.flush()
            await self._session.refresh(feedback)
            logger.info(
                "feedback_updated",
                feedback_id=str(feedback.id),
                message_id=str(message_id),
                tenant_id=str(tenant_id),
            )
        else:
            # Create new feedback
            feedback = Feedback(
                tenant_id=tenant_id,
                message_id=message_id,
                user_id=user_id,
                rating=data.rating,
                comment=data.comment,
            )
            self._session.add(feedback)
            await self._session.flush()
            await self._session.refresh(feedback)
            logger.info(
                "feedback_created",
                feedback_id=str(feedback.id),
                message_id=str(message_id),
                tenant_id=str(tenant_id),
            )

        return self._to_response(feedback)

    @staticmethod
    def _to_response(feedback: Feedback) -> FeedbackResponse:
        """Convert ORM model to Pydantic response."""
        return FeedbackResponse(
            id=UUID(str(feedback.id)),
            message_id=UUID(str(feedback.message_id)),
            user_id=UUID(str(feedback.user_id)),
            rating=feedback.rating,
            comment=feedback.comment,
            review_status=feedback.review_status,
            created_at=feedback.created_at,
        )
