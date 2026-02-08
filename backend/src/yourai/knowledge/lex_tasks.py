"""Celery tasks for Lex sidecar ingestion management.

Triggers Lex ingestion via ``docker exec`` on the lex-pipeline container,
tracks job status in PostgreSQL, and pushes SSE events to the admin user.
"""

from __future__ import annotations

import asyncio
from typing import Any
from uuid import UUID

import structlog

from yourai.core.celery_app import celery_app
from yourai.knowledge.tasks import _run_async

logger = structlog.get_logger()


@celery_app.task(  # type: ignore[untyped-decorator]
    name="lex.run_ingestion",
    queue="knowledge_ingest",
    bind=True,
    max_retries=0,
)
def run_lex_ingestion_task(
    self: Any,
    job_id: str,
    tenant_id: str,
    user_id: str,
) -> None:
    """Run a Lex ingestion job via docker exec."""
    log = logger.bind(tenant_id=tenant_id, user_id=user_id, job_id=job_id)
    log.info("lex_ingestion_task_started")

    _run_async(_run_ingestion(job_id, tenant_id, user_id, log))


async def _run_ingestion(
    job_id: str,
    tenant_id: str,
    user_id: str,
    log: Any,
) -> None:
    """Async implementation of the ingestion task."""
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from yourai.core.config import settings
    from yourai.knowledge.models import IngestionJobStatus, LexIngestionJob, _utcnow

    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    try:
        # 1. Load job, update to running
        async with session_factory() as session:
            from sqlalchemy import select

            q = select(LexIngestionJob).where(LexIngestionJob.id == UUID(job_id))
            job = (await session.execute(q)).scalar_one()

            job.status = IngestionJobStatus.RUNNING
            job.started_at = _utcnow()
            await session.commit()

            mode = job.mode
            parameters = dict(job.parameters) if job.parameters else {}

        # Publish SSE start event
        await _publish_event(settings, tenant_id, user_id, "started", job_id=job_id, mode=mode)

        # 2. Build docker exec command
        cmd = [
            "docker",
            "exec",
            settings.lex_pipeline_container,
            "python",
            "-m",
            "lex.ingest",
            "--mode",
            mode,
        ]

        # Add optional parameters
        if parameters.get("years"):
            for year in parameters["years"]:
                cmd.extend(["--year", str(year)])
        if parameters.get("limit"):
            cmd.extend(["--limit", str(parameters["limit"])])
        if parameters.get("pdf_fallback"):
            cmd.append("--pdf-fallback")

        log.info("lex_ingestion_exec", command=" ".join(cmd))

        # 3. Run subprocess
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )

        output_lines: list[str] = []
        assert process.stdout is not None
        async for raw_line in process.stdout:
            line = raw_line.decode("utf-8", errors="replace").rstrip()
            output_lines.append(line)
            log.debug("lex_ingestion_output", line=line)

            # Publish progress every 10 lines to avoid flooding
            if len(output_lines) % 10 == 0:
                await _publish_event(
                    settings,
                    tenant_id,
                    user_id,
                    "progress",
                    job_id=job_id,
                    message=line,
                )

        return_code = await process.wait()

        # 4. Update job based on result
        async with session_factory() as session:
            q = select(LexIngestionJob).where(LexIngestionJob.id == UUID(job_id))
            job = (await session.execute(q)).scalar_one()

            if return_code == 0:
                job.status = IngestionJobStatus.COMPLETED
                job.result = {
                    "return_code": 0,
                    "output_lines": len(output_lines),
                    "last_output": output_lines[-5:] if output_lines else [],
                }
                job.completed_at = _utcnow()
                log.info("lex_ingestion_completed", output_lines=len(output_lines))

                await _publish_event(
                    settings,
                    tenant_id,
                    user_id,
                    "completed",
                    job_id=job_id,
                    result=job.result,
                )
            else:
                error_msg = (
                    "\n".join(output_lines[-20:]) if output_lines else f"Exit code {return_code}"
                )
                job.status = IngestionJobStatus.FAILED
                job.error_message = error_msg
                job.completed_at = _utcnow()
                log.error("lex_ingestion_failed", return_code=return_code)

                await _publish_event(
                    settings,
                    tenant_id,
                    user_id,
                    "failed",
                    job_id=job_id,
                    error=error_msg,
                )

            await session.commit()

    except Exception as exc:
        log.error("lex_ingestion_task_error", error=str(exc), exc_info=True)

        # Update job as failed
        try:
            async with session_factory() as session:
                from sqlalchemy import select

                q = select(LexIngestionJob).where(LexIngestionJob.id == UUID(job_id))
                job = (await session.execute(q)).scalar_one_or_none()
                if job and job.status != IngestionJobStatus.COMPLETED:
                    job.status = IngestionJobStatus.FAILED
                    job.error_message = str(exc)
                    job.completed_at = _utcnow()
                    await session.commit()
        except Exception:
            log.error("lex_ingestion_job_update_failed", exc_info=True)

        await _publish_event(
            settings,
            tenant_id,
            user_id,
            "failed",
            job_id=job_id,
            error=str(exc),
        )

    finally:
        await engine.dispose()


@celery_app.task(  # type: ignore[untyped-decorator]
    name="lex.run_targeted_ingestion",
    queue="knowledge_ingest",
    bind=True,
    max_retries=0,
)
def run_lex_targeted_ingestion_task(
    self: Any,
    job_id: str,
    tenant_id: str,
    user_id: str,
) -> None:
    """Run a targeted Lex ingestion job (type+year filtering) via docker exec."""
    log = logger.bind(tenant_id=tenant_id, user_id=user_id, job_id=job_id)
    log.info("lex_targeted_ingestion_task_started")

    _run_async(_run_targeted_ingestion(job_id, tenant_id, user_id, log))


async def _run_targeted_ingestion(
    job_id: str,
    tenant_id: str,
    user_id: str,
    log: Any,
) -> None:
    """Async implementation of the targeted ingestion task."""
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from yourai.core.config import settings
    from yourai.knowledge.models import IngestionJobStatus, LexIngestionJob, _utcnow

    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    try:
        # 1. Load job, update to running
        async with session_factory() as session:
            q = select(LexIngestionJob).where(LexIngestionJob.id == UUID(job_id))
            job = (await session.execute(q)).scalar_one()

            job.status = IngestionJobStatus.RUNNING
            job.started_at = _utcnow()
            await session.commit()

            parameters = dict(job.parameters) if job.parameters else {}

        await _publish_event(
            settings, tenant_id, user_id, "started", job_id=job_id, mode="targeted"
        )

        # 2. Build docker exec command with type+year flags
        types = parameters.get("types", [])
        years = parameters.get("years", [])
        limit = parameters.get("limit")

        cmd = [
            "docker",
            "exec",
            settings.lex_pipeline_container,
            "python",
            "-m",
            "lex.ingest",
            "--mode",
            "legislation-unified",
        ]

        if types:
            cmd.extend(["--types", ",".join(types)])
        if years:
            cmd.extend(["--years", ",".join(str(y) for y in years)])
        if limit:
            cmd.extend(["--limit", str(limit)])
        cmd.append("--non-interactive")

        log.info("lex_targeted_ingestion_exec", command=" ".join(cmd))

        # 3. Run subprocess
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )

        output_lines: list[str] = []
        assert process.stdout is not None
        async for raw_line in process.stdout:
            line = raw_line.decode("utf-8", errors="replace").rstrip()
            output_lines.append(line)
            log.debug("lex_targeted_ingestion_output", line=line)

            if len(output_lines) % 10 == 0:
                await _publish_event(
                    settings,
                    tenant_id,
                    user_id,
                    "progress",
                    job_id=job_id,
                    message=line,
                )

        return_code = await process.wait()

        # 4. Update job based on result
        async with session_factory() as session:
            q = select(LexIngestionJob).where(LexIngestionJob.id == UUID(job_id))
            job = (await session.execute(q)).scalar_one()

            if return_code == 0:
                job.status = IngestionJobStatus.COMPLETED
                job.result = {
                    "return_code": 0,
                    "output_lines": len(output_lines),
                    "last_output": output_lines[-5:] if output_lines else [],
                }
                job.completed_at = _utcnow()
                log.info("lex_targeted_ingestion_completed", output_lines=len(output_lines))

                await _publish_event(
                    settings,
                    tenant_id,
                    user_id,
                    "completed",
                    job_id=job_id,
                    result=job.result,
                )
            else:
                error_msg = (
                    "\n".join(output_lines[-20:]) if output_lines else f"Exit code {return_code}"
                )
                job.status = IngestionJobStatus.FAILED
                job.error_message = error_msg
                job.completed_at = _utcnow()
                log.error("lex_targeted_ingestion_failed", return_code=return_code)

                await _publish_event(
                    settings,
                    tenant_id,
                    user_id,
                    "failed",
                    job_id=job_id,
                    error=error_msg,
                )

            await session.commit()

        # 5. Post-ingestion: sync Qdrant → DB tracking table
        if return_code == 0:
            try:
                async with session_factory() as session:
                    from yourai.knowledge.legislation_admin import LegislationAdminService

                    service = LegislationAdminService()
                    synced = await service.sync_index_from_qdrant(session, UUID(tenant_id))
                    await session.commit()
                    log.info("lex_targeted_ingestion_synced", synced=synced)
            except Exception:
                log.warning("lex_targeted_ingestion_sync_failed", exc_info=True)

    except Exception as exc:
        log.error("lex_targeted_ingestion_task_error", error=str(exc), exc_info=True)

        try:
            async with session_factory() as session:
                q = select(LexIngestionJob).where(LexIngestionJob.id == UUID(job_id))
                job = (await session.execute(q)).scalar_one_or_none()
                if job and job.status != IngestionJobStatus.COMPLETED:
                    job.status = IngestionJobStatus.FAILED
                    job.error_message = str(exc)
                    job.completed_at = _utcnow()
                    await session.commit()
        except Exception:
            log.error("lex_targeted_ingestion_job_update_failed", exc_info=True)

        await _publish_event(
            settings,
            tenant_id,
            user_id,
            "failed",
            job_id=job_id,
            error=str(exc),
        )

    finally:
        await engine.dispose()


async def _publish_event(
    settings: Any,
    tenant_id: str,
    user_id: str,
    event_kind: str,
    **kwargs: Any,
) -> None:
    """Publish an SSE event to the user's channel.

    Silently catches errors to avoid breaking the task.
    """
    try:
        from redis.asyncio import Redis

        from yourai.api.sse.channels import SSEChannel
        from yourai.api.sse.events import (
            IngestionCompletedEvent,
            IngestionFailedEvent,
            IngestionProgressEvent,
            IngestionStartedEvent,
        )
        from yourai.api.sse.publisher import EventPublisher

        redis = Redis.from_url(settings.redis_url)
        try:
            publisher = EventPublisher(redis)
            channel = SSEChannel.for_user(UUID(tenant_id), UUID(user_id))

            if event_kind == "started":
                event = IngestionStartedEvent(job_id=kwargs["job_id"], mode=kwargs["mode"])
            elif event_kind == "progress":
                event = IngestionProgressEvent(job_id=kwargs["job_id"], message=kwargs["message"])
            elif event_kind == "completed":
                event = IngestionCompletedEvent(job_id=kwargs["job_id"], result=kwargs["result"])
            elif event_kind == "failed":
                event = IngestionFailedEvent(job_id=kwargs["job_id"], error=kwargs["error"])
            else:
                return

            await publisher.publish(channel, event)
        finally:
            await redis.aclose()
    except Exception:
        logger.debug("lex_ingestion_sse_publish_failed", exc_info=True)
