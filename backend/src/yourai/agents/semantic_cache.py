"""Semantic cache service for caching AI responses based on embedding similarity.

Stores query embeddings and responses with TTL. Matches queries by cosine similarity
rather than exact text match, enabling cache hits for semantically similar questions.
"""

from __future__ import annotations

import struct
from datetime import datetime, timedelta
from uuid import UUID

import numpy as np
import structlog
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from yourai.agents.models import SemanticCacheEntry
from yourai.knowledge.embeddings import EmbeddingProvider, create_embedder

logger = structlog.get_logger()

# Cosine similarity threshold for cache hit (0.95 = 95% similar)
CACHE_HIT_THRESHOLD = 0.95


class SemanticCacheService:
    """Service for semantic cache operations."""

    def __init__(
        self, session: AsyncSession, embedder: EmbeddingProvider | None = None
    ) -> None:
        self._session = session
        self._embedder = embedder or create_embedder()

    async def check_cache(
        self,
        query: str,
        tenant_id: UUID,
    ) -> tuple[str, list[dict]] | None:  # type: ignore[type-arg]
        """Check if a semantically similar query is cached.

        Args:
            query: The user's query text
            tenant_id: Tenant UUID

        Returns:
            Tuple of (response, sources) if cache hit, None if miss
        """
        try:
            # Generate embedding for the query
            query_embedding_list = await self._embedder.embed_query(query)
            query_embedding_vec = np.array(query_embedding_list, dtype=np.float32)
            query_embedding = self._vec_to_bytes(query_embedding_vec)

            # Fetch all cache entries for this tenant that haven't expired
            now = datetime.utcnow()
            result = await self._session.execute(
                select(SemanticCacheEntry).where(
                    SemanticCacheEntry.tenant_id == tenant_id,
                    SemanticCacheEntry.query_embedding.isnot(None),
                )
            )
            entries = list(result.scalars().all())

            # Filter expired entries (created_at + ttl_seconds < now)
            valid_entries = []
            for entry in entries:
                if entry.created_at:
                    expiry = entry.created_at + timedelta(seconds=entry.ttl_seconds)
                    if expiry > now:
                        valid_entries.append(entry)

            if not valid_entries:
                logger.info(
                    "semantic_cache_miss",
                    tenant_id=str(tenant_id),
                    reason="no_valid_entries",
                )
                return None

            # Calculate cosine similarity with each entry
            best_match = None
            best_similarity = 0.0

            for entry in valid_entries:
                if not entry.query_embedding:
                    continue

                cached_embedding_vec = self._bytes_to_vec(entry.query_embedding)
                similarity = self._cosine_similarity(query_embedding_vec, cached_embedding_vec)

                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = entry

            # Check if best match exceeds threshold
            if best_match and best_similarity >= CACHE_HIT_THRESHOLD:
                # Increment hit count
                best_match.hit_count += 1
                await self._session.commit()

                logger.info(
                    "semantic_cache_hit",
                    tenant_id=str(tenant_id),
                    cache_entry_id=str(best_match.id),
                    similarity=best_similarity,
                    hit_count=best_match.hit_count,
                    query_text=query[:100],
                    cached_query_text=best_match.query_text[:100],
                )

                return (best_match.response, best_match.sources)  # type: ignore[return-value]

            logger.info(
                "semantic_cache_miss",
                tenant_id=str(tenant_id),
                reason="no_match_above_threshold",
                best_similarity=best_similarity,
            )
            return None

        except Exception as exc:
            logger.error(
                "semantic_cache_check_failed",
                tenant_id=str(tenant_id),
                error=str(exc),
                exc_info=True,
            )
            # On error, return None (cache miss) rather than failing the request
            return None

    async def store_in_cache(
        self,
        query: str,
        response: str,
        sources: list[dict],  # type: ignore[type-arg]
        tenant_id: UUID,
        ttl_seconds: int = 2592000,  # 30 days default
    ) -> None:
        """Store a query/response pair in the semantic cache.

        Args:
            query: The user's query text
            response: The assistant's response
            sources: List of sources used
            tenant_id: Tenant UUID
            ttl_seconds: Time-to-live in seconds (default 30 days)
        """
        try:
            # Generate embedding for the query
            query_embedding_list = await self._embedder.embed_query(query)
            query_embedding_vec = np.array(query_embedding_list, dtype=np.float32)
            query_embedding = self._vec_to_bytes(query_embedding_vec)

            # Create cache entry
            entry = SemanticCacheEntry(
                tenant_id=tenant_id,
                query_embedding=query_embedding,
                query_text=query,
                response=response,
                sources=sources,  # type: ignore[arg-type]
                ttl_seconds=ttl_seconds,
                hit_count=0,
            )
            self._session.add(entry)
            await self._session.commit()

            logger.info(
                "semantic_cache_stored",
                tenant_id=str(tenant_id),
                cache_entry_id=str(entry.id),
                ttl_seconds=ttl_seconds,
                query_text=query[:100],
            )

        except Exception as exc:
            logger.error(
                "semantic_cache_store_failed",
                tenant_id=str(tenant_id),
                error=str(exc),
                exc_info=True,
            )
            # Don't raise - caching is best-effort
            await self._session.rollback()

    async def cleanup_expired(self, tenant_id: UUID) -> int:
        """Remove expired cache entries for a tenant.

        Args:
            tenant_id: Tenant UUID

        Returns:
            Number of entries removed
        """
        now = datetime.utcnow()

        # Find expired entries
        result = await self._session.execute(
            select(SemanticCacheEntry).where(
                SemanticCacheEntry.tenant_id == tenant_id,
                SemanticCacheEntry.created_at.isnot(None),
            )
        )
        entries = list(result.scalars().all())

        expired_ids = []
        for entry in entries:
            if entry.created_at:
                expiry = entry.created_at + timedelta(seconds=entry.ttl_seconds)
                if expiry <= now:
                    expired_ids.append(entry.id)

        if expired_ids:
            await self._session.execute(
                delete(SemanticCacheEntry).where(SemanticCacheEntry.id.in_(expired_ids))
            )
            await self._session.commit()

            logger.info(
                "semantic_cache_cleanup",
                tenant_id=str(tenant_id),
                entries_removed=len(expired_ids),
            )

        return len(expired_ids)

    @staticmethod
    def _cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors."""
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        return float(dot_product / (norm1 * norm2))

    @staticmethod
    def _vec_to_bytes(vec: np.ndarray) -> bytes:
        """Convert numpy array to bytes for storage."""
        # Store as float32 for space efficiency
        return vec.astype(np.float32).tobytes()

    @staticmethod
    def _bytes_to_vec(data: bytes) -> np.ndarray:
        """Convert bytes back to numpy array."""
        # Calculate number of floats
        num_floats = len(data) // 4
        # Unpack bytes to float32 array
        return np.array(struct.unpack(f"{num_floats}f", data), dtype=np.float32)
