"""Persona routes — CRUD for conversation personas."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from yourai.agents.personas import PersonaService
from yourai.agents.schemas import CreatePersona, PersonaResponse, UpdatePersona
from yourai.core.database import get_db_session
from yourai.core.middleware import get_current_tenant, get_current_user, require_permission
from yourai.core.schemas import TenantConfig, UserResponse

router = APIRouter(prefix="/api/v1/personas", tags=["personas"])


@router.get("", response_model=list[PersonaResponse])
async def list_personas(
    tenant: TenantConfig = Depends(get_current_tenant),
    _user: UserResponse = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[PersonaResponse]:
    """List all personas for the current tenant."""
    service = PersonaService(session)
    return await service.list_personas(tenant.id)


@router.post(
    "",
    response_model=PersonaResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_persona(
    data: CreatePersona,
    tenant: TenantConfig = Depends(get_current_tenant),
    _perm: None = Depends(require_permission("create_persona")),
    session: AsyncSession = Depends(get_db_session),
) -> PersonaResponse:
    """Create a new persona. Requires create_persona permission."""
    service = PersonaService(session)
    result = await service.create_persona(tenant.id, data)
    await session.commit()
    return result


@router.get("/{persona_id}", response_model=PersonaResponse)
async def get_persona(
    persona_id: UUID,
    tenant: TenantConfig = Depends(get_current_tenant),
    _user: UserResponse = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> PersonaResponse:
    """Get a single persona by ID."""
    service = PersonaService(session)
    return await service.get_persona(persona_id, tenant.id)


@router.patch("/{persona_id}", response_model=PersonaResponse)
async def update_persona(
    persona_id: UUID,
    data: UpdatePersona,
    tenant: TenantConfig = Depends(get_current_tenant),
    _perm: None = Depends(require_permission("update_persona")),
    session: AsyncSession = Depends(get_db_session),
) -> PersonaResponse:
    """Update a persona. Requires update_persona permission."""
    service = PersonaService(session)
    result = await service.update_persona(persona_id, tenant.id, data)
    await session.commit()
    return result


@router.delete("/{persona_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_persona(
    persona_id: UUID,
    tenant: TenantConfig = Depends(get_current_tenant),
    _perm: None = Depends(require_permission("delete_persona")),
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    """Delete a persona. Requires delete_persona permission."""
    service = PersonaService(session)
    await service.delete_persona(persona_id, tenant.id)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{persona_id}/duplicate", response_model=PersonaResponse, status_code=status.HTTP_201_CREATED
)
async def duplicate_persona(
    persona_id: UUID,
    tenant: TenantConfig = Depends(get_current_tenant),
    _perm: None = Depends(require_permission("create_persona")),
    session: AsyncSession = Depends(get_db_session),
) -> PersonaResponse:
    """Duplicate an existing persona. Requires create_persona permission."""
    service = PersonaService(session)
    existing = await service.get_persona(persona_id, tenant.id)
    new_data = CreatePersona(
        name=f"{existing.name} (copy)",
        description=existing.description,
        system_instructions=existing.system_instructions,
        activated_skills=existing.activated_skills,
    )
    result = await service.create_persona(tenant.id, new_data)
    await session.commit()
    return result
