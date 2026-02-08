"""Case Law Worker — searches UK case law via Lex MCP.

Uses the Lex MCP client from WP4 to search UK court judgments and precedents.
"""

from __future__ import annotations

import json
from datetime import date
from typing import TYPE_CHECKING, Any
from uuid import UUID

import structlog

if TYPE_CHECKING:
    from mcp.types import CallToolResult

from yourai.agents.knowledge_schemas import CaseLawSource
from yourai.knowledge.exceptions import LexError
from yourai.knowledge.lex_mcp import LexMcpClient

logger = structlog.get_logger()


class CaseLawWorker:
    """Worker that searches UK case law via Lex MCP."""

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
    ) -> list[CaseLawSource]:
        """Search UK case law for relevant judgments.

        Args:
            query: User's query text
            tenant_id: Tenant ID for logging
            limit: Maximum number of results to return

        Returns:
            List of CaseLawSource objects with case citations and content

        Raises:
            RuntimeError: If not connected (call connect() first)
        """
        if self._client is None:
            raise RuntimeError("CaseLawWorker not connected. Call connect() first.")

        logger.info(
            "caselaw_worker_searching",
            tenant_id=str(tenant_id),
            query=query[:100],
            limit=limit,
        )

        try:
            # Check if Lex has case law tools available (not all instances do)
            available_tools = await self._client.list_tools()
            tool_names = {t.name for t in available_tools}

            # Try known case law tool names in order of preference
            caselaw_tool = None
            for name in ("search_cases", "search_caselaw", "search_judgments"):
                if name in tool_names:
                    caselaw_tool = name
                    break

            if caselaw_tool is None:
                logger.info(
                    "caselaw_worker_no_tools",
                    tenant_id=str(tenant_id),
                    msg="Lex instance does not expose case law search tools",
                )
                return []

            result = await self._client.call_tool(
                caselaw_tool,
                {"query": query, "limit": limit},
            )

            # Parse MCP result into CaseLawSource objects
            sources = self._parse_mcp_result(result)

            logger.info(
                "caselaw_worker_complete",
                tenant_id=str(tenant_id),
                sources_found=len(sources),
            )

            return sources

        except LexError as exc:
            logger.warning(
                "caselaw_worker_lex_error",
                tenant_id=str(tenant_id),
                error=str(exc),
            )
            # Case law search might not always be available or relevant
            # Return empty list rather than failing the entire invocation
            return []

        except Exception as exc:
            logger.error(
                "caselaw_worker_failed",
                tenant_id=str(tenant_id),
                error=str(exc),
                exc_info=True,
            )
            return []

    def _parse_mcp_result(self, result: CallToolResult) -> list[CaseLawSource]:
        """Parse MCP CallToolResult into CaseLawSource objects."""
        sources: list[CaseLawSource] = []

        for block in result.content:
            if not hasattr(block, "text"):
                continue

            try:
                data = json.loads(block.text) if isinstance(block.text, str) else block.text
                results = data if isinstance(data, list) else [data]

                for item in results:
                    source = self._parse_caselaw_item(item)
                    if source:
                        sources.append(source)

            except (json.JSONDecodeError, KeyError, TypeError) as exc:
                logger.warning(
                    "caselaw_worker_parse_error",
                    error=str(exc),
                    block_text=str(block.text)[:200],
                )
                continue

        return sources

    def _parse_caselaw_item(self, item: dict[str, Any]) -> CaseLawSource | None:
        """Parse a single case law search result item.

        Expected format from Lex MCP:
        {
            "case_name": "R v Smith",
            "citation": "[2020] EWCA Crim 123",
            "neutral_citation": "[2020] EWCA Crim 123",
            "court": "Court of Appeal (Criminal Division)",
            "judgment_date": "2020-03-15",
            "content": "...",
            "uri": "https://...",
            "score": 0.92
        }
        """
        try:
            case_name = item.get("case_name", item.get("name", "Unknown Case"))
            citation = item.get("citation", "")
            neutral_citation = item.get("neutral_citation")
            court = item.get("court", "Unknown Court")
            content = item.get("content", item.get("text", ""))
            uri = item.get("uri")
            score = float(item.get("score", 0.5))

            # Parse judgment date if provided
            judgment_date = None
            date_str = item.get("judgment_date", item.get("date"))
            if date_str:
                try:
                    judgment_date = date.fromisoformat(str(date_str))
                except (ValueError, TypeError):
                    pass  # Silently ignore date parsing errors

            return CaseLawSource(
                case_name=case_name,
                citation=citation,
                neutral_citation=neutral_citation,
                court=court,
                judgment_date=judgment_date,
                content=content,
                uri=uri,
                score=score,
            )

        except Exception as exc:
            logger.warning(
                "caselaw_worker_item_parse_error",
                error=str(exc),
                item=str(item)[:200],
            )
            return None
