"""Activity log service — query and export audit trail entries.

Every query filters by tenant_id at the application level.
"""

from __future__ import annotations

import csv
import io
from typing import TYPE_CHECKING
from uuid import UUID

import structlog
from sqlalchemy import func, select

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

from yourai.core.models import ActivityLog
from yourai.core.schemas import ActivityLogFilters, ActivityLogResponse, Page

logger = structlog.get_logger()


class ActivityLogService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_activity_logs(
        self, tenant_id: UUID, filters: ActivityLogFilters
    ) -> Page[ActivityLogResponse]:
        """List activity logs with pagination and filtering."""
        query = select(ActivityLog).where(ActivityLog.tenant_id == tenant_id)

        if filters.action is not None:
            query = query.where(ActivityLog.action == filters.action)
        if filters.user_id is not None:
            query = query.where(ActivityLog.user_id == filters.user_id)

        # Count total
        count_result = await self._session.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = count_result.scalar() or 0

        # Paginate
        offset = (filters.page - 1) * filters.page_size
        query = (
            query.order_by(ActivityLog.created_at.desc()).offset(offset).limit(filters.page_size)
        )

        result = await self._session.execute(query)
        logs = list(result.scalars().all())

        return Page(
            items=[self._to_response(log) for log in logs],
            total=total,
            page=filters.page,
            page_size=filters.page_size,
            has_next=(offset + filters.page_size) < total,
        )

    async def export_csv(self, tenant_id: UUID, filters: ActivityLogFilters) -> str:
        """Export activity logs as CSV content."""
        query = select(ActivityLog).where(ActivityLog.tenant_id == tenant_id)

        if filters.action is not None:
            query = query.where(ActivityLog.action == filters.action)
        if filters.user_id is not None:
            query = query.where(ActivityLog.user_id == filters.user_id)

        query = query.order_by(ActivityLog.created_at.desc()).limit(10000)
        result = await self._session.execute(query)
        logs = list(result.scalars().all())

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["id", "user_id", "action", "detail", "tags", "created_at"])
        for log in logs:
            writer.writerow(
                [
                    str(log.id),
                    str(log.user_id) if log.user_id else "",
                    log.action,
                    log.detail or "",
                    ",".join(log.tags) if log.tags else "",
                    str(log.created_at) if log.created_at else "",
                ]
            )
        return output.getvalue()

    @staticmethod
    def _to_response(log: ActivityLog) -> ActivityLogResponse:
        """Convert ORM model to Pydantic response."""
        return ActivityLogResponse(
            id=UUID(str(log.id)),
            tenant_id=UUID(str(log.tenant_id)),
            user_id=UUID(str(log.user_id)) if log.user_id else None,
            action=log.action,
            detail=log.detail,
            tags=log.tags,
            retention_expiry_at=log.retention_expiry_at,
            created_at=log.created_at,
        )
