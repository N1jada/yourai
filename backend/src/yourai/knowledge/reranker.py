"""Reranker abstraction with NoOp default implementation.

Provides a `Reranker` protocol for pluggable cross-encoder reranking.
The `NoOpReranker` simply truncates results to the requested limit.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from yourai.knowledge.schemas import SearchResult


class Reranker(Protocol):
    """Protocol for search result rerankers."""

    async def rerank(
        self,
        query: str,
        results: list[SearchResult],
        limit: int,
    ) -> list[SearchResult]:
        """Rerank search results and return top `limit` results."""
        ...


class NoOpReranker:
    """No-op reranker that simply truncates to the limit."""

    async def rerank(
        self,
        query: str,
        results: list[SearchResult],
        limit: int,
    ) -> list[SearchResult]:
        """Return first `limit` results without reranking."""
        return results[:limit]


def create_reranker() -> NoOpReranker:
    """Factory function to create the configured reranker."""
    return NoOpReranker()
