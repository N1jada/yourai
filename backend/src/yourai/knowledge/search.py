"""Hybrid search service: vector + BM25 with RRF fusion.

Full pipeline: embed query -> vector search (200) -> BM25 search (200) ->
RRF fusion (k=60) -> rerank -> enrich from DB.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

import structlog
from qdrant_client import models as qdrant_models
from sqlalchemy import select

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from yourai.core.enums import KnowledgeBaseCategory
from yourai.knowledge.embeddings import create_embedder
from yourai.knowledge.models import Document, DocumentChunk, KnowledgeBase
from yourai.knowledge.reranker import create_reranker
from yourai.knowledge.schemas import KeywordResult, SearchResult, VectorResult
from yourai.knowledge.vector_store import VectorStore

logger = structlog.get_logger()

_RRF_K = 60  # RRF constant


def rrf_fusion(
    vector_results: list[VectorResult],
    keyword_results: list[KeywordResult],
    k: int = _RRF_K,
) -> list[tuple[UUID, float]]:
    """Reciprocal Rank Fusion of vector and keyword search results.

    Returns list of (chunk_id, rrf_score) sorted by score descending.
    """
    scores: dict[UUID, float] = {}

    for rank, vr in enumerate(vector_results, start=1):
        scores[vr.chunk_id] = scores.get(vr.chunk_id, 0.0) + 1.0 / (k + rank)

    for rank, kr in enumerate(keyword_results, start=1):
        scores[kr.chunk_id] = scores.get(kr.chunk_id, 0.0) + 1.0 / (k + rank)

    sorted_results = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return sorted_results


class SearchService:
    """Hybrid search across a tenant's knowledge base."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def hybrid_search(
        self,
        query: str,
        tenant_id: UUID,
        categories: list[KnowledgeBaseCategory] | None = None,
        knowledge_base_ids: list[UUID] | None = None,
        limit: int = 10,
        similarity_threshold: float = 0.4,
    ) -> list[SearchResult]:
        """Full hybrid search pipeline."""
        log = logger.bind(tenant_id=str(tenant_id), query=query[:100])

        # Build Qdrant filter conditions
        filter_conditions = self._build_filter(tenant_id, categories, knowledge_base_ids)

        # Run vector and keyword search in parallel
        vector_results = await self.vector_search(
            query, tenant_id, limit=200, filter_conditions=filter_conditions
        )
        keyword_results = await self.keyword_search(
            query, tenant_id, limit=200, filter_conditions=filter_conditions
        )

        log.info(
            "search_raw_results",
            vector_count=len(vector_results),
            keyword_count=len(keyword_results),
        )

        # RRF fusion
        fused = rrf_fusion(vector_results, keyword_results)

        # Build initial SearchResults from fused scores
        chunk_ids = [chunk_id for chunk_id, _ in fused]

        # Build content map from both result sets
        content_map: dict[UUID, str] = {}
        for vr in vector_results:
            content_map[vr.chunk_id] = vr.content
        for kr in keyword_results:
            if kr.chunk_id not in content_map:
                content_map[kr.chunk_id] = kr.content

        # Enrich from database
        enriched = await self._enrich_results(chunk_ids, fused, content_map, tenant_id)

        # Reranker
        reranker = create_reranker()
        results = await reranker.rerank(query, enriched, limit)

        log.info("search_complete", result_count=len(results))
        return results

    async def vector_search(
        self,
        query: str,
        tenant_id: UUID,
        limit: int = 200,
        filter_conditions: qdrant_models.Filter | None = None,
    ) -> list[VectorResult]:
        """Raw vector similarity search."""
        embedder = create_embedder()
        query_vector = await embedder.embed_query(query)

        store = VectorStore()
        points = await store.vector_search(
            tenant_id, query_vector, limit=limit, filter_conditions=filter_conditions
        )

        return [
            VectorResult(
                chunk_id=UUID(str(p.id)),
                document_id=UUID(str(p.payload.get("document_id", "")))
                if p.payload
                else UUID(int=0),
                score=p.score,
                content=str(p.payload.get("content", "")) if p.payload else "",
            )
            for p in points
        ]

    async def keyword_search(
        self,
        query: str,
        tenant_id: UUID,
        limit: int = 200,
        filter_conditions: qdrant_models.Filter | None = None,
    ) -> list[KeywordResult]:
        """BM25 keyword search via Qdrant payload index."""
        store = VectorStore()
        points = await store.keyword_search(
            tenant_id, query, limit=limit, filter_conditions=filter_conditions
        )

        return [
            KeywordResult(
                chunk_id=UUID(str(p.id)),
                document_id=UUID(str(p.payload.get("document_id", "")))
                if p.payload
                else UUID(int=0),
                score=p.score,
                content=str(p.payload.get("content", "")) if p.payload else "",
            )
            for p in points
        ]

    def _build_filter(
        self,
        tenant_id: UUID,
        categories: list[KnowledgeBaseCategory] | None = None,
        knowledge_base_ids: list[UUID] | None = None,
    ) -> qdrant_models.Filter | None:
        """Build Qdrant filter conditions for category/KB filtering."""
        conditions: list[qdrant_models.FieldCondition] = []

        if knowledge_base_ids:
            conditions.append(
                qdrant_models.FieldCondition(
                    key="knowledge_base_id",
                    match=qdrant_models.MatchAny(any=[str(kb_id) for kb_id in knowledge_base_ids]),
                )
            )

        if not conditions:
            return None
        return qdrant_models.Filter(must=conditions)

    async def _enrich_results(
        self,
        chunk_ids: list[UUID],
        fused_scores: list[tuple[UUID, float]],
        content_map: dict[UUID, str],
        tenant_id: UUID,
    ) -> list[SearchResult]:
        """Enrich fused results with full document metadata from the database."""
        if not chunk_ids:
            return []

        # Load chunks with their documents and knowledge bases
        result = await self._session.execute(
            select(DocumentChunk, Document, KnowledgeBase)
            .join(Document, DocumentChunk.document_id == Document.id)
            .join(KnowledgeBase, Document.knowledge_base_id == KnowledgeBase.id)
            .where(
                DocumentChunk.id.in_(chunk_ids),
                DocumentChunk.tenant_id == tenant_id,
            )
        )
        rows = result.all()

        chunk_data: dict[UUID, tuple[DocumentChunk, Document, KnowledgeBase]] = {}
        for chunk, doc, kb in rows:
            chunk_data[chunk.id] = (chunk, doc, kb)

        # Build enriched results in fused score order
        enriched: list[SearchResult] = []
        for chunk_id, score in fused_scores:
            if chunk_id not in chunk_data:
                continue
            chunk, doc, kb = chunk_data[chunk_id]
            enriched.append(
                SearchResult(
                    chunk_id=chunk.id,
                    document_id=doc.id,
                    document_name=doc.name,
                    document_uri=doc.document_uri,
                    knowledge_base_category=kb.category,
                    chunk_index=chunk.chunk_index,
                    content=chunk.content,
                    contextual_prefix=chunk.contextual_prefix,
                    score=score,
                    source_uri=chunk.source_uri,
                    metadata=doc.metadata_,
                )
            )

        return enriched
