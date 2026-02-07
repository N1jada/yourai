"""Persona service — CRUD for personas table.

Every query filters by tenant_id at the application level (belt-and-braces with RLS).
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

import structlog
from sqlalchemy import select

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

from yourai.agents.models import Persona
from yourai.agents.schemas import CreatePersona, PersonaResponse, UpdatePersona
from yourai.core.exceptions import NotFoundError

logger = structlog.get_logger()


class PersonaService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_persona(self, persona_id: UUID, tenant_id: UUID) -> PersonaResponse:
        """Fetch a single persona by ID within tenant. Raises 404 if not found."""
        result = await self._session.execute(
            select(Persona).where(Persona.id == persona_id, Persona.tenant_id == tenant_id)
        )
        persona = result.scalar_one_or_none()
        if persona is None:
            raise NotFoundError("Persona not found.")
        return self._to_response(persona)

    async def list_personas(self, tenant_id: UUID) -> list[PersonaResponse]:
        """List all personas for a tenant, ordered by usage count descending."""
        result = await self._session.execute(
            select(Persona)
            .where(Persona.tenant_id == tenant_id)
            .order_by(Persona.usage_count.desc(), Persona.created_at.desc())
        )
        personas = list(result.scalars().all())
        return [self._to_response(p) for p in personas]

    async def create_persona(self, tenant_id: UUID, data: CreatePersona) -> PersonaResponse:
        """Create a new persona within a tenant."""
        persona = Persona(
            tenant_id=tenant_id,
            name=data.name,
            description=data.description,
            system_instructions=data.system_instructions,
            activated_skills=data.activated_skills,
        )
        self._session.add(persona)
        await self._session.flush()
        await self._session.refresh(persona)

        logger.info(
            "persona_created",
            persona_id=str(persona.id),
            tenant_id=str(tenant_id),
            name=data.name,
        )
        return self._to_response(persona)

    async def update_persona(
        self, persona_id: UUID, tenant_id: UUID, data: UpdatePersona
    ) -> PersonaResponse:
        """Update an existing persona."""
        result = await self._session.execute(
            select(Persona).where(Persona.id == persona_id, Persona.tenant_id == tenant_id)
        )
        persona = result.scalar_one_or_none()
        if persona is None:
            raise NotFoundError("Persona not found.")

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(persona, field, value)

        await self._session.flush()
        await self._session.refresh(persona)

        logger.info(
            "persona_updated",
            persona_id=str(persona_id),
            tenant_id=str(tenant_id),
        )
        return self._to_response(persona)

    async def delete_persona(self, persona_id: UUID, tenant_id: UUID) -> None:
        """Delete a persona (hard delete)."""
        result = await self._session.execute(
            select(Persona).where(Persona.id == persona_id, Persona.tenant_id == tenant_id)
        )
        persona = result.scalar_one_or_none()
        if persona is None:
            raise NotFoundError("Persona not found.")

        await self._session.delete(persona)
        await self._session.flush()

        logger.info(
            "persona_deleted",
            persona_id=str(persona_id),
            tenant_id=str(tenant_id),
        )

    @staticmethod
    def _to_response(persona: Persona) -> PersonaResponse:
        """Convert ORM model to Pydantic response.

        Manual construction avoids uuid_utils.UUID vs uuid.UUID issues (see MEMORY.md).
        """
        return PersonaResponse(
            id=UUID(str(persona.id)),
            tenant_id=UUID(str(persona.tenant_id)),
            name=persona.name,
            description=persona.description,
            system_instructions=persona.system_instructions,
            activated_skills=persona.activated_skills,
            usage_count=persona.usage_count,
            created_at=persona.created_at,
            updated_at=persona.updated_at,
        )
