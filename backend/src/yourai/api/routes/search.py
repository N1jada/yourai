"""Search route — hybrid search endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from yourai.core.database import get_db_session
from yourai.core.middleware import get_current_tenant
from yourai.core.schemas import TenantConfig
from yourai.knowledge.schemas import SearchRequest, SearchResult
from yourai.knowledge.search import SearchService

router = APIRouter(prefix="/api/v1/search", tags=["search"])


@router.post("", response_model=list[SearchResult])
async def search(
    data: SearchRequest,
    tenant: TenantConfig = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db_session),
) -> list[SearchResult]:
    """Perform hybrid search across the tenant's knowledge base."""
    service = SearchService(session)
    return await service.hybrid_search(
        query=data.query,
        tenant_id=tenant.id,
        categories=data.categories,
        knowledge_base_ids=data.knowledge_base_ids,
        limit=data.limit,
        similarity_threshold=data.similarity_threshold,
    )
