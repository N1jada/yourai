"""Document routes — upload, list, get, delete, versions, retry."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from yourai.core.database import get_db_session
from yourai.core.enums import DocumentProcessingState
from yourai.core.middleware import get_current_tenant, require_permission
from yourai.core.schemas import Page, TenantConfig
from yourai.knowledge.documents import DocumentService
from yourai.knowledge.schemas import DocumentFilters, DocumentResponse, DocumentVersion

router = APIRouter(tags=["documents"])


@router.post(
    "/api/v1/knowledge-bases/{knowledge_base_id}/documents",
    response_model=DocumentResponse,
    status_code=201,
)
async def upload_document(
    knowledge_base_id: UUID,
    file: UploadFile,
    tenant: TenantConfig = Depends(get_current_tenant),
    _perm: None = Depends(require_permission("upload_documents")),
    session: AsyncSession = Depends(get_db_session),
) -> DocumentResponse:
    """Upload a document to a knowledge base."""
    service = DocumentService(session)
    result = await service.upload(file, knowledge_base_id, tenant.id)
    await session.commit()
    return result


@router.get(
    "/api/v1/knowledge-bases/{knowledge_base_id}/documents",
    response_model=Page[DocumentResponse],
)
async def list_documents(
    knowledge_base_id: UUID,
    tenant: TenantConfig = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db_session),
    processing_state: DocumentProcessingState | None = Query(None),
    dead_letter: bool | None = Query(None),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> Page[DocumentResponse]:
    """List documents in a knowledge base."""
    filters = DocumentFilters(
        processing_state=processing_state,
        dead_letter=dead_letter,
        search=search,
        page=page,
        page_size=page_size,
    )
    service = DocumentService(session)
    return await service.list_documents(knowledge_base_id, tenant.id, filters)


@router.get("/api/v1/documents/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: UUID,
    tenant: TenantConfig = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db_session),
) -> DocumentResponse:
    """Get a document by ID."""
    service = DocumentService(session)
    return await service.get_document(document_id, tenant.id)


@router.delete("/api/v1/documents/{document_id}", status_code=204)
async def delete_document(
    document_id: UUID,
    tenant: TenantConfig = Depends(get_current_tenant),
    _perm: None = Depends(require_permission("delete_documents")),
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    """Delete a document."""
    service = DocumentService(session)
    await service.delete_document(document_id, tenant.id)
    await session.commit()
    return Response(status_code=204)


@router.get(
    "/api/v1/documents/{document_id}/versions",
    response_model=list[DocumentVersion],
)
async def get_document_versions(
    document_id: UUID,
    tenant: TenantConfig = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db_session),
) -> list[DocumentVersion]:
    """Get version history for a document."""
    service = DocumentService(session)
    return await service.get_versions(document_id, tenant.id)


@router.post(
    "/api/v1/documents/{document_id}/retry",
    response_model=DocumentResponse,
)
async def retry_document(
    document_id: UUID,
    tenant: TenantConfig = Depends(get_current_tenant),
    _perm: None = Depends(require_permission("upload_documents")),
    session: AsyncSession = Depends(get_db_session),
) -> DocumentResponse:
    """Retry processing a failed document."""
    service = DocumentService(session)
    result = await service.retry_failed(document_id, tenant.id)
    await session.commit()
    return result
