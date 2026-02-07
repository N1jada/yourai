"""Guardrail service — CRUD for guardrails table.

Every query filters by tenant_id at the application level.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

import structlog
from sqlalchemy import select

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

from yourai.core.exceptions import NotFoundError
from yourai.core.models import Guardrail
from yourai.core.schemas import CreateGuardrail, GuardrailResponse, UpdateGuardrail

logger = structlog.get_logger()


class GuardrailService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_guardrails(self, tenant_id: UUID) -> list[GuardrailResponse]:
        """List all guardrails for a tenant."""
        result = await self._session.execute(
            select(Guardrail)
            .where(Guardrail.tenant_id == tenant_id)
            .order_by(Guardrail.created_at.desc())
        )
        guardrails = list(result.scalars().all())
        return [self._to_response(g) for g in guardrails]

    async def get_guardrail(self, guardrail_id: UUID, tenant_id: UUID) -> GuardrailResponse:
        """Fetch a single guardrail. Raises 404 if not found."""
        result = await self._session.execute(
            select(Guardrail).where(
                Guardrail.id == guardrail_id,
                Guardrail.tenant_id == tenant_id,
            )
        )
        guardrail = result.scalar_one_or_none()
        if guardrail is None:
            raise NotFoundError("Guardrail not found.")
        return self._to_response(guardrail)

    async def create_guardrail(self, tenant_id: UUID, data: CreateGuardrail) -> GuardrailResponse:
        """Create a new guardrail."""
        guardrail = Guardrail(
            tenant_id=tenant_id,
            name=data.name,
            description=data.description,
            configuration_rules=data.configuration_rules,
        )
        self._session.add(guardrail)
        await self._session.flush()
        await self._session.refresh(guardrail)

        logger.info(
            "guardrail_created",
            guardrail_id=str(guardrail.id),
            tenant_id=str(tenant_id),
            name=data.name,
        )
        return self._to_response(guardrail)

    async def update_guardrail(
        self, guardrail_id: UUID, tenant_id: UUID, data: UpdateGuardrail
    ) -> GuardrailResponse:
        """Update an existing guardrail."""
        result = await self._session.execute(
            select(Guardrail).where(
                Guardrail.id == guardrail_id,
                Guardrail.tenant_id == tenant_id,
            )
        )
        guardrail = result.scalar_one_or_none()
        if guardrail is None:
            raise NotFoundError("Guardrail not found.")

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(guardrail, field, value)

        await self._session.flush()
        await self._session.refresh(guardrail)

        logger.info(
            "guardrail_updated",
            guardrail_id=str(guardrail_id),
            tenant_id=str(tenant_id),
        )
        return self._to_response(guardrail)

    async def delete_guardrail(self, guardrail_id: UUID, tenant_id: UUID) -> None:
        """Delete a guardrail."""
        result = await self._session.execute(
            select(Guardrail).where(
                Guardrail.id == guardrail_id,
                Guardrail.tenant_id == tenant_id,
            )
        )
        guardrail = result.scalar_one_or_none()
        if guardrail is None:
            raise NotFoundError("Guardrail not found.")

        await self._session.delete(guardrail)
        await self._session.flush()

        logger.info(
            "guardrail_deleted",
            guardrail_id=str(guardrail_id),
            tenant_id=str(tenant_id),
        )

    @staticmethod
    def _to_response(guardrail: Guardrail) -> GuardrailResponse:
        """Convert ORM model to Pydantic response."""
        return GuardrailResponse(
            id=UUID(str(guardrail.id)),
            tenant_id=UUID(str(guardrail.tenant_id)),
            name=guardrail.name,
            description=guardrail.description,
            status=guardrail.status,
            configuration_rules=guardrail.configuration_rules,
            created_at=guardrail.created_at,
            updated_at=guardrail.updated_at,
        )
