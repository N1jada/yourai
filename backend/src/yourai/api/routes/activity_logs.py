"""Activity log routes — query and export audit trail."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from yourai.core.activity_logs import ActivityLogService
from yourai.core.database import get_db_session
from yourai.core.middleware import get_current_tenant, require_permission
from yourai.core.schemas import (
    ActivityLogFilters,
    ActivityLogResponse,
    Page,
    TenantConfig,
)

router = APIRouter(prefix="/api/v1/activity-logs", tags=["activity-logs"])


@router.get("", response_model=Page[ActivityLogResponse])
async def list_activity_logs(
    tenant: TenantConfig = Depends(get_current_tenant),
    _perm: None = Depends(require_permission("list_activity_logs")),
    session: AsyncSession = Depends(get_db_session),
    action: str | None = Query(None),
    user_id: UUID | None = Query(None),
    tag: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
) -> Page[ActivityLogResponse]:
    """List activity logs with pagination and filtering."""
    filters = ActivityLogFilters(
        action=action,
        user_id=user_id,
        tag=tag,
        page=page,
        page_size=page_size,
    )
    service = ActivityLogService(session)
    return await service.list_activity_logs(tenant.id, filters)


@router.get("/export")
async def export_activity_logs(
    tenant: TenantConfig = Depends(get_current_tenant),
    _perm: None = Depends(require_permission("export_activity_logs")),
    session: AsyncSession = Depends(get_db_session),
    action: str | None = Query(None),
    user_id: UUID | None = Query(None),
    tag: str | None = Query(None),
) -> Response:
    """Export activity logs as CSV."""
    filters = ActivityLogFilters(action=action, user_id=user_id, tag=tag)
    service = ActivityLogService(session)
    csv_content = await service.export_csv(tenant.id, filters)
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="activity-logs.csv"'},
    )
