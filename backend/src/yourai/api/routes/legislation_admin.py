"""Legislation admin routes — Lex health, search, and detail lookups."""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from yourai.core.middleware import get_current_tenant, require_permission
from yourai.core.schemas import TenantConfig
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
