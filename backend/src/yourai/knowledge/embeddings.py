"""Embedding providers for document chunks.

Provides an `EmbeddingProvider` protocol and a `VoyageEmbedder` implementation.
Factory function `create_embedder()` returns the configured provider.
"""

from __future__ import annotations

from typing import Protocol

import structlog

from yourai.core.config import settings

logger = structlog.get_logger()


class EmbeddingProvider(Protocol):
    """Protocol for embedding providers."""

    @property
    def model_name(self) -> str: ...

    @property
    def dimensions(self) -> int: ...

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of document texts."""
        ...

    async def embed_query(self, text: str) -> list[float]:
        """Embed a single query text."""
        ...


class VoyageEmbedder:
    """Voyage AI embedding provider for document chunks."""

    def __init__(self) -> None:
        import voyageai

        self._client = voyageai.AsyncClient(api_key=settings.voyage_api_key)  # type: ignore[attr-defined]
        self._model = settings.embedding_model
        self._dims = settings.embedding_dimensions
        self._batch_size = settings.embedding_batch_size

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def dimensions(self) -> int:
        return self._dims

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed document texts in batches."""
        all_embeddings: list[list[float]] = []
        for i in range(0, len(texts), self._batch_size):
            batch = texts[i : i + self._batch_size]
            result = await self._client.embed(
                batch,
                model=self._model,
                input_type="document",
            )
            all_embeddings.extend(result.embeddings)  # type: ignore[arg-type]
            logger.debug(
                "embeddings_batch_complete",
                batch_index=i // self._batch_size,
                batch_size=len(batch),
            )
        return all_embeddings

    async def embed_query(self, text: str) -> list[float]:
        """Embed a single query text with query-optimised input type."""
        result = await self._client.embed(
            [text],
            model=self._model,
            input_type="query",
        )
        return result.embeddings[0]  # type: ignore[return-value]


def create_embedder() -> VoyageEmbedder:
    """Factory function to create the configured embedding provider."""
    if settings.embedding_provider == "voyage":
        return VoyageEmbedder()
    raise ValueError(f"Unknown embedding provider: {settings.embedding_provider}")
