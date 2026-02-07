"""Guardrail routes — CRUD for AI guardrail configurations."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from yourai.core.database import get_db_session
from yourai.core.guardrails import GuardrailService
from yourai.core.middleware import get_current_tenant, require_permission
from yourai.core.schemas import (
    CreateGuardrail,
    GuardrailResponse,
    TenantConfig,
    UpdateGuardrail,
)

router = APIRouter(prefix="/api/v1/guardrails", tags=["guardrails"])


@router.get("", response_model=list[GuardrailResponse])
async def list_guardrails(
    tenant: TenantConfig = Depends(get_current_tenant),
    _perm: None = Depends(require_permission("list_guardrails")),
    session: AsyncSession = Depends(get_db_session),
) -> list[GuardrailResponse]:
    """List all guardrails for the current tenant."""
    service = GuardrailService(session)
    return await service.list_guardrails(tenant.id)


@router.post(
    "",
    response_model=GuardrailResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_guardrail(
    data: CreateGuardrail,
    tenant: TenantConfig = Depends(get_current_tenant),
    _perm: None = Depends(require_permission("create_guardrail")),
    session: AsyncSession = Depends(get_db_session),
) -> GuardrailResponse:
    """Create a new guardrail. Requires create_guardrail permission."""
    service = GuardrailService(session)
    result = await service.create_guardrail(tenant.id, data)
    await session.commit()
    return result


@router.get("/{guardrail_id}", response_model=GuardrailResponse)
async def get_guardrail(
    guardrail_id: UUID,
    tenant: TenantConfig = Depends(get_current_tenant),
    _perm: None = Depends(require_permission("view_guardrail")),
    session: AsyncSession = Depends(get_db_session),
) -> GuardrailResponse:
    """Get a single guardrail by ID."""
    service = GuardrailService(session)
    return await service.get_guardrail(guardrail_id, tenant.id)


@router.patch("/{guardrail_id}", response_model=GuardrailResponse)
async def update_guardrail(
    guardrail_id: UUID,
    data: UpdateGuardrail,
    tenant: TenantConfig = Depends(get_current_tenant),
    _perm: None = Depends(require_permission("update_guardrail")),
    session: AsyncSession = Depends(get_db_session),
) -> GuardrailResponse:
    """Update a guardrail. Requires update_guardrail permission."""
    service = GuardrailService(session)
    result = await service.update_guardrail(guardrail_id, tenant.id, data)
    await session.commit()
    return result


@router.delete("/{guardrail_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_guardrail(
    guardrail_id: UUID,
    tenant: TenantConfig = Depends(get_current_tenant),
    _perm: None = Depends(require_permission("delete_guardrail")),
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    """Delete a guardrail. Requires delete_guardrail permission."""
    service = GuardrailService(session)
    await service.delete_guardrail(guardrail_id, tenant.id)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
