"""Legislation Worker — searches UK legislation via Lex MCP.

Uses the Lex MCP client from WP4 to search UK legislation and statutes.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any
from uuid import UUID

import structlog

if TYPE_CHECKING:
    from mcp.types import CallToolResult

from yourai.agents.knowledge_schemas import LegislationSource, VerificationStatus
from yourai.knowledge.exceptions import LexError
from yourai.knowledge.lex_mcp import LexMcpClient

logger = structlog.get_logger()


class LegislationWorker:
    """Worker that searches UK legislation via Lex MCP."""

    def __init__(self, lex_mcp_url: str) -> None:
        self._lex_mcp_url = lex_mcp_url
        self._client: LexMcpClient | None = None

    async def connect(self) -> None:
        """Establish MCP connection. Call before using search()."""
        if self._client is None:
            self._client = LexMcpClient(self._lex_mcp_url)
            await self._client.connect()

    async def disconnect(self) -> None:
        """Close MCP connection. Call when done."""
        if self._client is not None:
            await self._client.disconnect()
            self._client = None

    async def search(
        self,
        query: str,
        tenant_id: UUID,
        limit: int = 5,
    ) -> list[LegislationSource]:
        """Search UK legislation for relevant provisions.

        Args:
            query: User's query text
            tenant_id: Tenant ID for logging
            limit: Maximum number of results to return

        Returns:
            List of LegislationSource objects with act citations and content

        Raises:
            RuntimeError: If not connected (call connect() first)
        """
        if self._client is None:
            raise RuntimeError("LegislationWorker not connected. Call connect() first.")

        logger.info(
            "legislation_worker_searching",
            tenant_id=str(tenant_id),
            query=query[:100],
            limit=limit,
        )

        try:
            # Call Lex MCP search_for_legislation_sections tool
            result = await self._client.call_tool(
                "search_for_legislation_sections",
                {"query": query, "size": limit, "include_text": True},
            )

            # Parse MCP result into LegislationSource objects
            sources = self._parse_mcp_result(result)

            logger.info(
                "legislation_worker_complete",
                tenant_id=str(tenant_id),
                sources_found=len(sources),
            )

            return sources

        except LexError as exc:
            logger.error(
                "legislation_worker_lex_error",
                tenant_id=str(tenant_id),
                error=str(exc),
            )
            # Return empty list on Lex error rather than failing entire invocation
            return []

        except Exception as exc:
            logger.error(
                "legislation_worker_failed",
                tenant_id=str(tenant_id),
                error=str(exc),
                exc_info=True,
            )
            return []

    def _parse_mcp_result(self, result: CallToolResult) -> list[LegislationSource]:
        """Parse MCP CallToolResult into LegislationSource objects.

        MCP result content is a list of content blocks. For search results,
        we expect text blocks containing JSON with legislation data.
        """
        sources: list[LegislationSource] = []

        for block in result.content:
            # MCP content blocks have different types (text, image, resource, etc.)
            # For legislation search, we expect text blocks with JSON data
            if not hasattr(block, "text"):
                continue

            try:
                # Parse the JSON content from the text block
                data = json.loads(block.text) if isinstance(block.text, str) else block.text

                # Handle Lex API envelope {"results": [...]} or raw array/object
                if isinstance(data, dict) and "results" in data:
                    results = data["results"]
                elif isinstance(data, list):
                    results = data
                else:
                    results = [data]

                for item in results:
                    source = self._parse_legislation_item(item)
                    if source:
                        sources.append(source)

            except (json.JSONDecodeError, KeyError, TypeError) as exc:
                logger.warning(
                    "legislation_worker_parse_error",
                    error=str(exc),
                    block_text=str(block.text)[:200],
                )
                continue

        return sources

    def _parse_legislation_item(self, item: dict[str, Any]) -> LegislationSource | None:
        """Parse a single legislation search result item.

        Handles actual Lex API response format:
        {
            "title": "Immigration Act 2014",
            "description": "...",
            "uri": "http://www.legislation.gov.uk/ukpga/2014/22/made",
            "year": 2014,
            "number": 2928,
            "type": "ukpga",
            "category": "primary",
            "sections": [{"number": "42", "provision_type": "section", ...}],
            "text": "..."
        }
        """
        try:
            act_name = item.get("title", item.get("act_name", "Unknown Act"))
            year = item.get("year")

            # Lex nests sections; extract first section if present
            sections = item.get("sections", [])
            section = item.get("section")
            subsection = item.get("subsection")
            if not section and sections:
                first_sec = sections[0] if isinstance(sections, list) else None
                if first_sec and isinstance(first_sec, dict):
                    section = first_sec.get("number")

            # Content may be in text, content, or description fields
            content = item.get("text", "") or item.get("content", "") or item.get("description", "")
            # Also check section-level text
            if not content and sections and isinstance(sections, list):
                for sec in sections:
                    if isinstance(sec, dict) and sec.get("text"):
                        content = sec["text"]
                        break

            uri = item.get("uri", "")
            # Score may be at top level or in a section
            score = float(item.get("score", 0.5))

            # Determine if historical (pre-1963)
            is_historical = year is not None and year < 1963

            return LegislationSource(
                act_name=act_name,
                year=year,
                section=str(section) if section else None,
                subsection=str(subsection) if subsection else None,
                content=content,
                uri=uri,
                score=score,
                is_historical=is_historical,
                verification_status=VerificationStatus.VERIFIED,
            )

        except Exception as exc:
            logger.warning(
                "legislation_worker_item_parse_error",
                error=str(exc),
                item=str(item)[:200],
            )
            return None
