"""Feedback routes — submit feedback on messages."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from yourai.agents.feedback import FeedbackService
from yourai.agents.schemas import CreateFeedback, FeedbackResponse
from yourai.core.database import get_db_session
from yourai.core.middleware import get_current_tenant, get_current_user
from yourai.core.schemas import TenantConfig, UserResponse

router = APIRouter(prefix="/api/v1/messages", tags=["feedback"])


@router.post(
    "/{message_id}/feedback",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_feedback(
    message_id: UUID,
    data: CreateFeedback,
    tenant: TenantConfig = Depends(get_current_tenant),
    user: UserResponse = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> FeedbackResponse:
    """Submit or update feedback on a message."""
    service = FeedbackService(session)
    result = await service.submit_feedback(message_id, user.id, tenant.id, data)
    await session.commit()
    return result
