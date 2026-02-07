"""Conversation template routes — stub returning empty list."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from yourai.agents.schemas import ConversationTemplateResponse
from yourai.core.middleware import get_current_tenant, get_current_user
from yourai.core.schemas import TenantConfig, UserResponse

router = APIRouter(prefix="/api/v1/conversation-templates", tags=["templates"])


@router.get("", response_model=list[ConversationTemplateResponse])
async def list_templates(
    _tenant: TenantConfig = Depends(get_current_tenant),
    _user: UserResponse = Depends(get_current_user),
) -> list[ConversationTemplateResponse]:
    """List conversation templates. Stub returning empty list until templates are implemented."""
    return []
