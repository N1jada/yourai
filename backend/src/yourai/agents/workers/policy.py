"""Policy Worker — searches internal company policy documents.

Uses the hybrid search service from WP3 to find relevant policy content.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

import structlog

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

from yourai.agents.knowledge_schemas import PolicySource
from yourai.core.enums import KnowledgeBaseCategory
from yourai.knowledge.search import SearchService

logger = structlog.get_logger()


class PolicyWorker:
    """Worker that searches internal company policy documents."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._search_service = SearchService(session)

    async def search(
        self,
        query: str,
        tenant_id: UUID,
        limit: int = 5,
    ) -> list[PolicySource]:
        """Search company policy documents for relevant content.

        Args:
            query: User's query text
            tenant_id: Tenant ID for isolation
            limit: Maximum number of results to return

        Returns:
            List of PolicySource objects with document citations and content
        """
        logger.info(
            "policy_worker_searching",
            tenant_id=str(tenant_id),
            query=query[:100],
            limit=limit,
        )

        try:
            # Use hybrid search from WP3 to search company policy category
            results = await self._search_service.hybrid_search(
                query=query,
                tenant_id=tenant_id,
                categories=[KnowledgeBaseCategory.COMPANY_POLICY],
                limit=limit,
                similarity_threshold=0.3,  # Lower threshold for recall
            )

            # Convert SearchResult objects to PolicySource objects
            policy_sources = []
            for result in results:
                # Extract section from metadata if available
                section = result.metadata.get("section") if result.metadata else None

                policy_source = PolicySource(
                    document_id=str(result.document_id),
                    document_name=result.document_name,
                    section=section if isinstance(section, str) else None,
                    content=result.content,
                    score=result.score,
                    metadata=result.metadata,
                )
                policy_sources.append(policy_source)

            logger.info(
                "policy_worker_complete",
                tenant_id=str(tenant_id),
                sources_found=len(policy_sources),
            )

            return policy_sources

        except Exception as exc:
            logger.error(
                "policy_worker_failed",
                tenant_id=str(tenant_id),
                error=str(exc),
                exc_info=True,
            )
            # Return empty list on error rather than failing entire invocation
            return []
