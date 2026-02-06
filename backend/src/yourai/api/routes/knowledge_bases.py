"""Knowledge base routes — CRUD and sync."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from yourai.core.database import get_db_session
from yourai.core.middleware import get_current_tenant, require_permission
from yourai.core.schemas import TenantConfig
from yourai.knowledge.knowledge_base import KnowledgeBaseService
from yourai.knowledge.schemas import (
    CreateKnowledgeBase,
    KnowledgeBaseResponse,
    UpdateKnowledgeBase,
)

router = APIRouter(prefix="/api/v1/knowledge-bases", tags=["knowledge-bases"])


@router.get("", response_model=list[KnowledgeBaseResponse])
async def list_knowledge_bases(
    tenant: TenantConfig = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db_session),
) -> list[KnowledgeBaseResponse]:
    """List all knowledge bases for the current tenant."""
    service = KnowledgeBaseService(session)
    return await service.list_knowledge_bases(tenant.id)


@router.post("", response_model=KnowledgeBaseResponse, status_code=201)
async def create_knowledge_base(
    data: CreateKnowledgeBase,
    tenant: TenantConfig = Depends(get_current_tenant),
    _perm: None = Depends(require_permission("create_knowledge_base")),
    session: AsyncSession = Depends(get_db_session),
) -> KnowledgeBaseResponse:
    """Create a new knowledge base."""
    service = KnowledgeBaseService(session)
    result = await service.create_knowledge_base(tenant.id, data)
    await session.commit()
    return result


@router.get("/{knowledge_base_id}", response_model=KnowledgeBaseResponse)
async def get_knowledge_base(
    knowledge_base_id: UUID,
    tenant: TenantConfig = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db_session),
) -> KnowledgeBaseResponse:
    """Get a knowledge base by ID."""
    service = KnowledgeBaseService(session)
    return await service.get_knowledge_base(knowledge_base_id, tenant.id)


@router.patch("/{knowledge_base_id}", response_model=KnowledgeBaseResponse)
async def update_knowledge_base(
    knowledge_base_id: UUID,
    data: UpdateKnowledgeBase,
    tenant: TenantConfig = Depends(get_current_tenant),
    _perm: None = Depends(require_permission("create_knowledge_base")),
    session: AsyncSession = Depends(get_db_session),
) -> KnowledgeBaseResponse:
    """Update a knowledge base."""
    service = KnowledgeBaseService(session)
    result = await service.update_knowledge_base(knowledge_base_id, tenant.id, data)
    await session.commit()
    return result


@router.delete("/{knowledge_base_id}", status_code=204)
async def delete_knowledge_base(
    knowledge_base_id: UUID,
    tenant: TenantConfig = Depends(get_current_tenant),
    _perm: None = Depends(require_permission("delete_knowledge_base")),
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    """Delete a knowledge base and all its documents."""
    service = KnowledgeBaseService(session)
    await service.delete_knowledge_base(knowledge_base_id, tenant.id)
    await session.commit()
    return Response(status_code=204)


@router.post("/{knowledge_base_id}/sync", status_code=202)
async def sync_knowledge_base(
    knowledge_base_id: UUID,
    tenant: TenantConfig = Depends(get_current_tenant),
    _perm: None = Depends(require_permission("sync_knowledge_base")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    """Trigger async sync for a catalog-type knowledge base."""
    service = KnowledgeBaseService(session)
    await service.sync_knowledge_base(knowledge_base_id, tenant.id)
    return {"message": "Sync initiated."}
