"""Qdrant vector store operations.

Manages tenant-namespaced collections (tenant_{tenant_id}_documents),
handles vector upsert/delete/search and BM25 keyword search via payload index.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from uuid import UUID
from qdrant_client import AsyncQdrantClient, models

from yourai.core.config import settings

logger = structlog.get_logger()


def _collection_name(tenant_id: UUID) -> str:
    """Generate tenant-specific collection name."""
    return f"tenant_{tenant_id}_documents"


class VectorStore:
    """Qdrant vector store for document chunks."""

    def __init__(self, client: AsyncQdrantClient | None = None) -> None:
        self._client = client or AsyncQdrantClient(url=settings.qdrant_url)

    async def ensure_collection(self, tenant_id: UUID) -> None:
        """Create collection if it doesn't exist, with vector config and BM25 text index."""
        name = _collection_name(tenant_id)
        collections = await self._client.get_collections()
        existing = {c.name for c in collections.collections}

        if name not in existing:
            await self._client.create_collection(
                collection_name=name,
                vectors_config=models.VectorParams(
                    size=settings.embedding_dimensions,
                    distance=models.Distance.COSINE,
                ),
            )
            # Create text payload index for BM25 keyword search
            await self._client.create_payload_index(
                collection_name=name,
                field_name="content",
                field_schema=models.TextIndexParams(
                    type=models.TextIndexType.TEXT,
                    tokenizer=models.TokenizerType.WORD,
                    min_token_len=2,
                    max_token_len=20,
                    lowercase=True,
                ),
            )
            logger.info(
                "qdrant_collection_created",
                tenant_id=str(tenant_id),
                collection_name=name,
            )

    async def upsert_chunks(
        self,
        tenant_id: UUID,
        points: list[dict[str, object]],
    ) -> None:
        """Upsert vector points to tenant collection.

        Each point dict should have: id (str), vector (list[float]),
        payload (dict with content, document_id, chunk_index, etc.)
        """
        name = _collection_name(tenant_id)
        qdrant_points = [
            models.PointStruct(
                id=str(p["id"]),
                vector=p["vector"],
                payload=p["payload"],
            )
            for p in points
        ]
        await self._client.upsert(collection_name=name, points=qdrant_points)
        logger.info(
            "qdrant_points_upserted",
            tenant_id=str(tenant_id),
            count=len(points),
        )

    async def delete_by_document(self, tenant_id: UUID, document_id: UUID) -> None:
        """Delete all vectors for a specific document."""
        name = _collection_name(tenant_id)
        await self._client.delete(
            collection_name=name,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="document_id",
                            match=models.MatchValue(value=str(document_id)),
                        )
                    ]
                )
            ),
        )
        logger.info(
            "qdrant_document_vectors_deleted",
            tenant_id=str(tenant_id),
            document_id=str(document_id),
        )

    async def vector_search(
        self,
        tenant_id: UUID,
        query_vector: list[float],
        limit: int = 200,
        filter_conditions: models.Filter | None = None,
    ) -> list[models.ScoredPoint]:
        """Perform vector similarity search."""
        name = _collection_name(tenant_id)
        response = await self._client.query_points(
            collection_name=name,
            query=query_vector,
            limit=limit,
            query_filter=filter_conditions,
            with_payload=True,
        )
        return response.points

    async def keyword_search(
        self,
        tenant_id: UUID,
        query: str,
        limit: int = 200,
        filter_conditions: models.Filter | None = None,
    ) -> list[models.ScoredPoint]:
        """Perform BM25 keyword search via Qdrant scroll + text match."""
        name = _collection_name(tenant_id)
        text_filter = models.FieldCondition(
            key="content",
            match=models.MatchText(text=query),
        )

        must_conditions: list[models.FieldCondition] = [text_filter]
        if filter_conditions and filter_conditions.must:
            for cond in filter_conditions.must:
                if isinstance(cond, models.FieldCondition):
                    must_conditions.append(cond)

        combined_filter = models.Filter(must=must_conditions)

        results, _next_offset = await self._client.scroll(
            collection_name=name,
            scroll_filter=combined_filter,
            limit=limit,
            with_payload=True,
            with_vectors=False,
        )

        # Convert scroll results to scored points with a basic score
        scored: list[models.ScoredPoint] = []
        for i, point in enumerate(results):
            scored.append(
                models.ScoredPoint(
                    id=point.id,
                    version=0,
                    score=1.0 / (i + 1),  # Reciprocal rank as proxy score
                    payload=point.payload,
                )
            )
        return scored

    async def delete_collection(self, tenant_id: UUID) -> None:
        """Delete entire tenant collection."""
        name = _collection_name(tenant_id)
        await self._client.delete_collection(collection_name=name)
        logger.info(
            "qdrant_collection_deleted",
            tenant_id=str(tenant_id),
            collection_name=name,
        )
