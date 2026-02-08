"""Legislation admin routes — Lex health, search, detail lookups, and ingestion."""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: TCH002 — FastAPI DI needs runtime type

from yourai.core.database import get_db_session  # noqa: TCH001
from yourai.core.middleware import get_current_tenant, get_current_user, require_permission
from yourai.core.schemas import TenantConfig, UserResponse  # noqa: TCH001
from yourai.knowledge.legislation_admin import LegislationAdminService

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/admin/legislation", tags=["legislation-admin"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class LegislationSearchRequest(BaseModel):
    query: str
    year_from: int | None = None
    year_to: int | None = None
    legislation_type: list[str] | None = None
    offset: int = 0
    limit: int = Field(default=10, le=50)


class LexOverviewResponse(BaseModel):
    status: str
    active_url: str
    primary_url: str
    fallback_url: str
    is_using_fallback: bool
    stats: dict[str, Any] | None = None


class LegislationSearchResponse(BaseModel):
    results: list[dict[str, Any]]
    total: int
    offset: int
    limit: int


class LegislationDetailResponse(BaseModel):
    legislation: dict[str, Any]
    sections: list[dict[str, Any]]
    amendments: list[dict[str, Any]]


class HealthCheckResponse(BaseModel):
    primary_healthy: bool
    status: str
    active_url: str


class ForcePrimaryResponse(BaseModel):
    status: str
    active_url: str


class QdrantCollectionInfo(BaseModel):
    name: str
    points_count: int = 0
    status: str = "unknown"


class PrimaryStatusResponse(BaseModel):
    healthy: bool
    qdrant_url: str
    collections: list[QdrantCollectionInfo]


class TriggerIngestionRequest(BaseModel):
    mode: str = Field(description="Ingestion mode: daily, full, or amendments_led")
    years: list[int] | None = None
    limit: int | None = None
    pdf_fallback: bool = False


class IngestionJobResponse(BaseModel):
    id: str
    tenant_id: str | None = None
    mode: str
    status: str
    triggered_by: str | None = None
    parameters: dict[str, Any] = {}
    result: dict[str, Any] | None = None
    error_message: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class IngestionJobListResponse(BaseModel):
    items: list[IngestionJobResponse]
    total: int
    offset: int
    limit: int


# ---------------------------------------------------------------------------
# Indexed legislation schemas
# ---------------------------------------------------------------------------


class IndexedLegislationItem(BaseModel):
    qdrant_point_id: str = ""
    legislation_id: str = ""
    title: str | None = None
    type: str | None = None
    year: int | None = None
    number: int | None = None
    category: str | None = None
    status_text: str | None = None
    section_count: int = 0
    uri: str | None = None
    enactment_date: str | None = None


class IndexedLegislationResponse(BaseModel):
    items: list[IndexedLegislationItem]
    next_offset: str | None = None


class RemoveLegislationRequest(BaseModel):
    legislation_ids: list[str]


class RemoveLegislationResponse(BaseModel):
    removed: int
    errors: list[str] = []


class SyncIndexResponse(BaseModel):
    synced: int


class TargetedIngestionRequest(BaseModel):
    types: list[str] = Field(description="Legislation types e.g. ['ukpga', 'uksi']")
    years: list[int] = Field(description="Years to ingest")
    limit: int | None = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/overview", response_model=LexOverviewResponse)
async def get_overview(
    tenant: TenantConfig = Depends(get_current_tenant),
    _perm: None = Depends(require_permission("manage_legislation")),
) -> LexOverviewResponse:
    """Return Lex connection status and dataset statistics."""
    service = LegislationAdminService()
    data = await service.get_overview()
    return LexOverviewResponse(**data)


@router.post("/search", response_model=LegislationSearchResponse)
async def search_legislation(
    body: LegislationSearchRequest,
    tenant: TenantConfig = Depends(get_current_tenant),
    _perm: None = Depends(require_permission("manage_legislation")),
) -> LegislationSearchResponse:
    """Search indexed legislation via the active Lex endpoint."""
    service = LegislationAdminService()
    data = await service.search(
        query=body.query,
        year_from=body.year_from,
        year_to=body.year_to,
        legislation_type=body.legislation_type,
        offset=body.offset,
        limit=body.limit,
    )
    return LegislationSearchResponse(**data)


@router.get("/detail/{legislation_type}/{year}/{number}")
async def get_legislation_detail(
    legislation_type: str,
    year: int,
    number: int,
    tenant: TenantConfig = Depends(get_current_tenant),
    _perm: None = Depends(require_permission("manage_legislation")),
) -> LegislationDetailResponse:
    """Lookup a piece of legislation with sections and amendments."""
    from fastapi.responses import JSONResponse

    from yourai.knowledge.exceptions import (
        LexConnectionError,
        LexError,
        LexNotFoundError,
        LexTimeoutError,
    )

    service = LegislationAdminService()
    try:
        data = await service.get_detail(legislation_type, year, number)
    except LexNotFoundError:
        return JSONResponse(
            status_code=404,
            content={"message": f"Legislation {legislation_type}/{year}/{number} not found in Lex"},
        )
    except (LexConnectionError, LexTimeoutError) as exc:
        logger.warning("legislation_detail_lex_unreachable", error=str(exc))
        return JSONResponse(
            status_code=502,
            content={"message": "Lex API is unreachable"},
        )
    except LexError as exc:
        logger.warning("legislation_detail_lex_error", error=str(exc))
        return JSONResponse(
            status_code=502,
            content={"message": "Lex API returned an error"},
        )
    return LegislationDetailResponse(**data)


@router.post("/health-check", response_model=HealthCheckResponse)
async def trigger_health_check(
    tenant: TenantConfig = Depends(get_current_tenant),
    _perm: None = Depends(require_permission("manage_legislation")),
) -> HealthCheckResponse:
    """Trigger a primary Lex health check."""
    service = LegislationAdminService()
    data = await service.check_health()
    return HealthCheckResponse(**data)


@router.post("/force-primary", response_model=ForcePrimaryResponse)
async def force_primary(
    tenant: TenantConfig = Depends(get_current_tenant),
    _perm: None = Depends(require_permission("manage_legislation")),
) -> ForcePrimaryResponse:
    """Reset failover to use the primary Lex endpoint."""
    service = LegislationAdminService()
    data = service.force_primary()
    return ForcePrimaryResponse(**data)


# ---------------------------------------------------------------------------
# Self-hosted Qdrant status
# ---------------------------------------------------------------------------


@router.get("/primary-status", response_model=PrimaryStatusResponse)
async def get_primary_status(
    tenant: TenantConfig = Depends(get_current_tenant),
    _perm: None = Depends(require_permission("manage_legislation")),
) -> PrimaryStatusResponse:
    """Return self-hosted Lex Qdrant collection statistics."""
    service = LegislationAdminService()
    data = await service.get_primary_status()
    return PrimaryStatusResponse(**data)


# ---------------------------------------------------------------------------
# Indexed legislation
# ---------------------------------------------------------------------------


@router.get("/indexed", response_model=IndexedLegislationResponse)
async def list_indexed_legislation(
    type_filter: str | None = None,
    year_filter: int | None = None,
    limit: int = 20,
    offset_id: str | None = None,
    tenant: TenantConfig = Depends(get_current_tenant),
    _perm: None = Depends(require_permission("manage_legislation")),
) -> IndexedLegislationResponse:
    """List legislation indexed in the self-hosted Qdrant."""
    service = LegislationAdminService()
    data = await service.list_indexed_legislation(
        type_filter=type_filter,
        year_filter=year_filter,
        limit=limit,
        offset_id=offset_id,
    )
    items = [
        IndexedLegislationItem(
            qdrant_point_id=str(it.get("qdrant_point_id", "")),
            legislation_id=str(it.get("id", "")),
            title=it.get("title"),
            type=it.get("type"),
            year=it.get("year"),
            number=it.get("number"),
            category=it.get("category"),
            status_text=it.get("status_text"),
            section_count=it.get("section_count", 0),
            uri=it.get("uri"),
            enactment_date=it.get("enactment_date"),
        )
        for it in data.get("items", [])
    ]
    return IndexedLegislationResponse(items=items, next_offset=data.get("next_offset"))


@router.post("/indexed/sync", response_model=SyncIndexResponse)
async def sync_legislation_index(
    tenant: TenantConfig = Depends(get_current_tenant),
    _perm: None = Depends(require_permission("manage_legislation")),
    session: AsyncSession = Depends(get_db_session),
) -> SyncIndexResponse:
    """Sync the DB tracking table with the current Qdrant state."""
    service = LegislationAdminService()
    synced = await service.sync_index_from_qdrant(session, tenant.id)
    await session.commit()
    return SyncIndexResponse(synced=synced)


@router.post("/indexed/remove", response_model=RemoveLegislationResponse)
async def remove_indexed_legislation(
    body: RemoveLegislationRequest,
    tenant: TenantConfig = Depends(get_current_tenant),
    _perm: None = Depends(require_permission("manage_legislation")),
    session: AsyncSession = Depends(get_db_session),
    user: UserResponse = Depends(get_current_user),
) -> RemoveLegislationResponse:
    """Delete legislation from the self-hosted Qdrant instance."""
    service = LegislationAdminService()
    data = await service.remove_legislation(
        session=session,
        tenant_id=tenant.id,
        user_id=user.id,
        legislation_ids=body.legislation_ids,
    )
    await session.commit()
    return RemoveLegislationResponse(**data)


@router.post("/ingest-targeted", response_model=IngestionJobResponse)
async def trigger_targeted_ingestion(
    body: TargetedIngestionRequest,
    tenant: TenantConfig = Depends(get_current_tenant),
    _perm: None = Depends(require_permission("manage_legislation")),
    session: AsyncSession = Depends(get_db_session),
    user: UserResponse = Depends(get_current_user),
) -> IngestionJobResponse:
    """Trigger a targeted ingestion by type+year."""
    service = LegislationAdminService()
    data = await service.trigger_targeted_ingestion(
        session=session,
        tenant_id=tenant.id,
        user_id=user.id,
        types=body.types,
        years=body.years,
        limit=body.limit,
    )
    await session.commit()
    return IngestionJobResponse(**data)


# ---------------------------------------------------------------------------
# Ingestion
# ---------------------------------------------------------------------------


@router.post("/ingestion", response_model=IngestionJobResponse)
async def trigger_ingestion(
    body: TriggerIngestionRequest,
    tenant: TenantConfig = Depends(get_current_tenant),
    _perm: None = Depends(require_permission("manage_legislation")),
    session: AsyncSession = Depends(get_db_session),
    user: UserResponse = Depends(get_current_user),
) -> IngestionJobResponse:
    """Trigger a Lex ingestion job."""

    service = LegislationAdminService()
    params = {}
    if body.years:
        params["years"] = body.years
    if body.limit:
        params["limit"] = body.limit
    if body.pdf_fallback:
        params["pdf_fallback"] = body.pdf_fallback

    data = await service.trigger_ingestion(
        session=session,
        tenant_id=tenant.id,
        user_id=user.id,
        mode=body.mode,
        parameters=params,
    )
    await session.commit()
    return IngestionJobResponse(**data)


@router.get("/ingestion", response_model=IngestionJobListResponse)
async def list_ingestion_jobs(
    limit: int = 20,
    offset: int = 0,
    tenant: TenantConfig = Depends(get_current_tenant),
    _perm: None = Depends(require_permission("manage_legislation")),
    session: AsyncSession = Depends(get_db_session),
) -> IngestionJobListResponse:
    """List ingestion jobs for the current tenant."""
    service = LegislationAdminService()
    data = await service.get_ingestion_jobs(
        session=session,
        tenant_id=tenant.id,
        limit=limit,
        offset=offset,
    )
    return IngestionJobListResponse(**data)


@router.get("/ingestion/{job_id}", response_model=IngestionJobResponse)
async def get_ingestion_job(
    job_id: str,
    tenant: TenantConfig = Depends(get_current_tenant),
    _perm: None = Depends(require_permission("manage_legislation")),
    session: AsyncSession = Depends(get_db_session),
) -> IngestionJobResponse:
    """Get a single ingestion job by ID."""
    from uuid import UUID

    from fastapi import HTTPException

    service = LegislationAdminService()
    data = await service.get_ingestion_job(
        session=session,
        tenant_id=tenant.id,
        job_id=UUID(job_id),
    )
    if data is None:
        raise HTTPException(status_code=404, detail="Ingestion job not found")
    return IngestionJobResponse(**data)
