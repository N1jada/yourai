"""Celery task wrappers for the document processing pipeline.

Each task creates an event loop to run the async pipeline functions.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any
from uuid import UUID

import structlog

from yourai.core.celery_app import celery_app

if TYPE_CHECKING:
    from collections.abc import Coroutine

logger = structlog.get_logger()


def _run_async(coro: Coroutine[Any, Any, None]) -> None:
    """Run an async coroutine in a new event loop."""
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(  # type: ignore[untyped-decorator]
    name="knowledge.process_document",
    queue="knowledge_ingest",
    bind=True,
    max_retries=3,
    default_retry_delay=1,
)
def process_document_task(self: Any, document_id: str, tenant_id: str) -> None:
    """Celery task wrapper for the document processing pipeline."""
    log = logger.bind(tenant_id=tenant_id, document_id=document_id)
    log.info("process_document_task_started")

    async def _run() -> None:
        from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

        from yourai.core.config import settings
        from yourai.knowledge.pipeline import process_document

        engine = create_async_engine(settings.database_url)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as session:
            await process_document(session, UUID(document_id), UUID(tenant_id))
            await session.commit()
        await engine.dispose()

    try:
        _run_async(_run())
    except Exception as exc:
        log.error("process_document_task_failed", error=str(exc), exc_info=True)
        raise self.retry(exc=exc) from exc


@celery_app.task(  # type: ignore[untyped-decorator]
    name="knowledge.delete_document_vectors",
    queue="knowledge_ingest",
)
def delete_document_vectors_task(document_id: str, tenant_id: str) -> None:
    """Celery task to remove all vectors for a document from Qdrant."""
    log = logger.bind(tenant_id=tenant_id, document_id=document_id)
    log.info("delete_document_vectors_task_started")

    async def _run() -> None:
        from yourai.knowledge.vector_store import VectorStore

        store = VectorStore()
        await store.delete_by_document(UUID(tenant_id), UUID(document_id))

    _run_async(_run())
    log.info("delete_document_vectors_task_complete")
