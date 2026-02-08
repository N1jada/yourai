"""Admin service for Lex legislation management — health, search, detail lookups, and ingestion.

Wraps :class:`LexHealthManager` and :class:`LexRestClient` to provide
a single interface for the legislation admin routes.  Also manages
self-hosted Lex Qdrant status and ingestion job orchestration.
"""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

from yourai.knowledge.exceptions import LexConnectionError, LexError, LexTimeoutError
from yourai.knowledge.lex_health import LexHealthManager, get_lex_health

logger = structlog.get_logger()


class LegislationAdminService:
    """Read-only admin proxy to the Lex legislation API."""

    def __init__(self, health_manager: LexHealthManager | None = None) -> None:
        self._health = health_manager or get_lex_health()

    # ------------------------------------------------------------------
    # Overview
    # ------------------------------------------------------------------

    async def get_overview(self) -> dict[str, Any]:
        """Return combined health status and dataset statistics.

        Returns a dict with keys: status, active_url, primary_url,
        fallback_url, is_using_fallback, stats (or None if unreachable).
        """
        overview: dict[str, Any] = {
            "status": self._health.status,
            "active_url": self._health.active_url,
            "primary_url": self._health._primary_url,
            "fallback_url": self._health._fallback_url,
            "is_using_fallback": self._health.is_using_fallback,
            "stats": None,
        }

        client = self._health.get_rest_client(timeout=10.0)
        try:
            overview["stats"] = await client.get_stats()
        except (LexConnectionError, LexTimeoutError, LexError) as exc:
            logger.warning("legislation_admin_stats_failed", error=str(exc))
        finally:
            await client.aclose()

        return overview

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    async def search(
        self,
        *,
        query: str,
        year_from: int | None = None,
        year_to: int | None = None,
        legislation_type: list[str] | None = None,
        offset: int = 0,
        limit: int = 10,
    ) -> dict[str, Any]:
        """Forward a legislation search to the active Lex endpoint."""
        client = self._health.get_rest_client()
        try:
            result = await client.search_legislation(
                query,
                year_from=year_from,
                year_to=year_to,
                legislation_type=legislation_type,
                offset=offset,
                limit=limit,
                include_text=False,
            )
            return result.model_dump()
        finally:
            await client.aclose()

    # ------------------------------------------------------------------
    # Detail
    # ------------------------------------------------------------------

    async def get_detail(
        self,
        legislation_type: str,
        year: int,
        number: int,
    ) -> dict[str, Any]:
        """Lookup a single piece of legislation with its sections and amendments."""
        client = self._health.get_rest_client()
        try:
            legislation = await client.lookup_legislation(legislation_type, year, number)

            sections = await client.get_legislation_sections(legislation.id, limit=200)

            amendments: list[dict[str, Any]] = []
            try:
                raw = await client.search_amendments(legislation.id)
                amendments = [a.model_dump() for a in raw]
            except LexError:
                pass  # Amendments are optional — don't fail the whole request

            return {
                "legislation": legislation.model_dump(),
                "sections": [s.model_dump() for s in sections],
                "amendments": amendments,
            }
        finally:
            await client.aclose()

    # ------------------------------------------------------------------
    # Health management
    # ------------------------------------------------------------------

    async def check_health(self) -> dict[str, Any]:
        """Trigger a primary health check and return the result."""
        primary_healthy = await self._health.check_health()
        return {
            "primary_healthy": primary_healthy,
            "status": self._health.status,
            "active_url": self._health.active_url,
        }

    def force_primary(self) -> dict[str, Any]:
        """Reset failover to use the primary endpoint."""
        self._health.force_primary()
        return {
            "status": self._health.status,
            "active_url": self._health.active_url,
        }

    # ------------------------------------------------------------------
    # Self-hosted Qdrant status
    # ------------------------------------------------------------------

    async def get_primary_status(self) -> dict[str, Any]:
        """Query the self-hosted Lex Qdrant for collection statistics."""
        from yourai.core.config import settings
        from yourai.knowledge.lex_qdrant_status import CollectionInfo, LexQdrantStatusClient

        client = LexQdrantStatusClient(settings.lex_qdrant_url)
        try:
            healthy = await client.is_healthy()
            collections: list[CollectionInfo] = []
            if healthy:
                collections = await client.list_collections()
            return {
                "healthy": healthy,
                "qdrant_url": settings.lex_qdrant_url,
                "collections": [c.model_dump() for c in collections],
            }
        except Exception as exc:
            logger.warning("lex_qdrant_status_failed", error=str(exc))
            return {
                "healthy": False,
                "qdrant_url": settings.lex_qdrant_url,
                "collections": [],
            }
        finally:
            await client.aclose()

    # ------------------------------------------------------------------
    # Ingestion jobs
    # ------------------------------------------------------------------

    async def trigger_ingestion(
        self,
        session: AsyncSession,
        tenant_id: UUID,
        user_id: UUID,
        mode: str,
        parameters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create an ingestion job record and dispatch a Celery task."""
        import uuid_utils

        from yourai.knowledge.models import IngestionJobStatus, LexIngestionJob

        job = LexIngestionJob(
            id=uuid_utils.uuid7(),
            tenant_id=tenant_id,
            mode=mode,
            status=IngestionJobStatus.PENDING,
            triggered_by=user_id,
            parameters=parameters or {},
        )
        session.add(job)
        await session.flush()

        # Dispatch Celery task
        from yourai.knowledge.lex_tasks import run_lex_ingestion_task

        run_lex_ingestion_task.delay(
            job_id=str(job.id),
            tenant_id=str(tenant_id),
            user_id=str(user_id),
        )

        logger.info(
            "lex_ingestion_triggered",
            tenant_id=str(tenant_id),
            user_id=str(user_id),
            job_id=str(job.id),
            mode=mode,
        )

        return {
            "id": str(job.id),
            "mode": job.mode,
            "status": job.status,
            "parameters": job.parameters,
            "created_at": job.created_at.isoformat() if job.created_at else None,
        }

    async def get_ingestion_jobs(
        self,
        session: AsyncSession,
        tenant_id: UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> dict[str, Any]:
        """List ingestion jobs for a tenant, newest first."""
        from sqlalchemy import func, select

        from yourai.knowledge.models import LexIngestionJob

        # Count total
        count_q = (
            select(func.count())
            .select_from(LexIngestionJob)
            .where(LexIngestionJob.tenant_id == tenant_id)
        )
        total = (await session.execute(count_q)).scalar_one()

        # Fetch page
        q = (
            select(LexIngestionJob)
            .where(LexIngestionJob.tenant_id == tenant_id)
            .order_by(LexIngestionJob.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        rows = (await session.execute(q)).scalars().all()

        return {
            "items": [self._job_to_dict(j) for j in rows],
            "total": total,
            "offset": offset,
            "limit": limit,
        }

    async def get_ingestion_job(
        self,
        session: AsyncSession,
        tenant_id: UUID,
        job_id: UUID,
    ) -> dict[str, Any] | None:
        """Fetch a single ingestion job by ID."""
        from sqlalchemy import select

        from yourai.knowledge.models import LexIngestionJob

        q = select(LexIngestionJob).where(
            LexIngestionJob.id == job_id,
            LexIngestionJob.tenant_id == tenant_id,
        )
        row = (await session.execute(q)).scalar_one_or_none()
        if row is None:
            return None
        return self._job_to_dict(row)

    # ------------------------------------------------------------------
    # Indexed legislation
    # ------------------------------------------------------------------

    async def list_indexed_legislation(
        self,
        type_filter: str | None = None,
        year_filter: int | None = None,
        limit: int = 20,
        offset_id: str | None = None,
    ) -> dict[str, Any]:
        """Scroll indexed legislation from self-hosted Qdrant.

        Returns items enriched with section counts plus a ``next_offset``
        cursor for pagination.
        """
        from yourai.core.config import settings
        from yourai.knowledge.lex_qdrant_status import LexQdrantStatusClient

        client = LexQdrantStatusClient(settings.lex_qdrant_url)
        try:
            result = await client.scroll_legislation(
                type_filter=type_filter,
                year_filter=year_filter,
                limit=limit,
                offset_id=offset_id,
            )
            # Enrich each item with section count
            for item in result["items"]:
                leg_id = item.get("id", "")
                if leg_id:
                    try:
                        item["section_count"] = await client.count_sections_for_legislation(
                            str(leg_id)
                        )
                    except Exception:
                        item["section_count"] = 0
                else:
                    item["section_count"] = 0
            return result
        finally:
            await client.aclose()

    async def sync_index_from_qdrant(
        self,
        session: AsyncSession,
        tenant_id: UUID,
    ) -> int:
        """Scroll all legislation points from Qdrant and upsert into DB tracking table.

        Returns the number of items synced.
        """
        import uuid_utils
        from sqlalchemy import select

        from yourai.core.config import settings
        from yourai.knowledge.lex_qdrant_status import LexQdrantStatusClient
        from yourai.knowledge.models import LexLegislationIndex, LexLegislationStatus, _utcnow

        client = LexQdrantStatusClient(settings.lex_qdrant_url)
        synced = 0
        try:
            offset_id: str | None = None
            while True:
                result = await client.scroll_legislation(
                    limit=100,
                    offset_id=offset_id,
                )
                items = result["items"]
                if not items:
                    break

                for item in items:
                    leg_id = str(item.get("id", ""))
                    if not leg_id:
                        continue

                    leg_type = item.get("type")
                    year = item.get("year")
                    number = item.get("number")
                    title = item.get("title")

                    # Get section count
                    section_count = 0
                    with contextlib.suppress(Exception):
                        section_count = await client.count_sections_for_legislation(leg_id)

                    # Check if already exists
                    q = select(LexLegislationIndex).where(
                        LexLegislationIndex.tenant_id == tenant_id,
                        LexLegislationIndex.legislation_id == leg_id,
                    )
                    existing = (await session.execute(q)).scalar_one_or_none()

                    if existing:
                        existing.title = title
                        existing.section_count = section_count
                        existing.status = LexLegislationStatus.INDEXED
                        existing.updated_at = _utcnow()
                    else:
                        new_item = LexLegislationIndex(
                            id=uuid_utils.uuid7(),
                            tenant_id=tenant_id,
                            legislation_id=leg_id,
                            legislation_type=str(leg_type) if leg_type else None,
                            year=int(year) if year is not None else None,
                            number=int(number) if number is not None else None,
                            title=str(title) if title else None,
                            status=LexLegislationStatus.INDEXED,
                            section_count=section_count,
                            qdrant_point_ids={"legislation": item.get("qdrant_point_id")},
                        )
                        session.add(new_item)

                    synced += 1

                await session.flush()

                offset_id = result.get("next_offset")
                if not offset_id:
                    break

            return synced
        finally:
            await client.aclose()

    async def remove_legislation(
        self,
        session: AsyncSession,
        tenant_id: UUID,
        user_id: UUID,
        legislation_ids: list[str],
    ) -> dict[str, Any]:
        """Delete legislation from Qdrant and update DB tracking.

        Returns ``{"removed": N, "errors": [...]}``.
        """
        from sqlalchemy import select

        from yourai.core.config import settings
        from yourai.knowledge.lex_qdrant_status import LexQdrantStatusClient
        from yourai.knowledge.models import LexLegislationIndex, LexLegislationStatus, _utcnow

        client = LexQdrantStatusClient(settings.lex_qdrant_url)
        removed = 0
        errors: list[str] = []

        try:
            for leg_id in legislation_ids:
                # Mark as removing in DB
                q = select(LexLegislationIndex).where(
                    LexLegislationIndex.tenant_id == tenant_id,
                    LexLegislationIndex.legislation_id == leg_id,
                )
                row = (await session.execute(q)).scalar_one_or_none()
                if row:
                    row.status = LexLegislationStatus.REMOVING
                    await session.flush()

                # Delete from Qdrant
                try:
                    result = await client.delete_legislation_by_id(leg_id)
                    if result.get("legislation") or result.get("sections"):
                        if row:
                            row.status = LexLegislationStatus.REMOVED
                            row.removed_at = _utcnow()
                        removed += 1
                    else:
                        errors.append(f"Failed to remove {leg_id} from Qdrant")
                        if row:
                            row.status = LexLegislationStatus.FAILED
                except Exception as exc:
                    errors.append(f"{leg_id}: {exc!s}")
                    if row:
                        row.status = LexLegislationStatus.FAILED

            await session.flush()

            logger.info(
                "lex_legislation_removed",
                tenant_id=str(tenant_id),
                user_id=str(user_id),
                removed=removed,
                errors=len(errors),
            )

            return {"removed": removed, "errors": errors}
        finally:
            await client.aclose()

    async def trigger_targeted_ingestion(
        self,
        session: AsyncSession,
        tenant_id: UUID,
        user_id: UUID,
        types: list[str],
        years: list[int],
        limit: int | None = None,
    ) -> dict[str, Any]:
        """Create a targeted ingestion job and dispatch the Celery task."""
        import uuid_utils

        from yourai.knowledge.models import IngestionJobStatus, IngestionMode, LexIngestionJob

        parameters: dict[str, Any] = {"types": types, "years": years}
        if limit:
            parameters["limit"] = limit

        job = LexIngestionJob(
            id=uuid_utils.uuid7(),
            tenant_id=tenant_id,
            mode=IngestionMode.TARGETED,
            status=IngestionJobStatus.PENDING,
            triggered_by=user_id,
            parameters=parameters,
        )
        session.add(job)
        await session.flush()

        from yourai.knowledge.lex_tasks import run_lex_targeted_ingestion_task

        run_lex_targeted_ingestion_task.delay(
            job_id=str(job.id),
            tenant_id=str(tenant_id),
            user_id=str(user_id),
        )

        logger.info(
            "lex_targeted_ingestion_triggered",
            tenant_id=str(tenant_id),
            user_id=str(user_id),
            job_id=str(job.id),
            types=types,
            years=years,
        )

        return {
            "id": str(job.id),
            "mode": job.mode,
            "status": job.status,
            "parameters": job.parameters,
            "created_at": job.created_at.isoformat() if job.created_at else None,
        }

    @staticmethod
    def _job_to_dict(job: object) -> dict[str, Any]:
        """Convert a LexIngestionJob ORM instance to a dict."""

        return {
            "id": str(job.id),  # type: ignore[attr-defined]
            "tenant_id": str(job.tenant_id),  # type: ignore[attr-defined]
            "mode": job.mode,  # type: ignore[attr-defined]
            "status": job.status,  # type: ignore[attr-defined]
            "triggered_by": str(job.triggered_by),  # type: ignore[attr-defined]
            "parameters": job.parameters,  # type: ignore[attr-defined]
            "result": job.result,  # type: ignore[attr-defined]
            "error_message": job.error_message,  # type: ignore[attr-defined]
            "started_at": job.started_at.isoformat() if job.started_at else None,  # type: ignore[attr-defined]
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,  # type: ignore[attr-defined]
            "created_at": job.created_at.isoformat() if job.created_at else None,  # type: ignore[attr-defined]
            "updated_at": job.updated_at.isoformat() if job.updated_at else None,  # type: ignore[attr-defined]
        }
