"""MCP client for interactive Lex tool calls during AI agent conversations."""

from __future__ import annotations

from contextlib import AsyncExitStack
from typing import TYPE_CHECKING, Any

import structlog
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from yourai.knowledge.exceptions import LexConnectionError, LexError

if TYPE_CHECKING:
    from mcp.types import CallToolResult, Tool

logger = structlog.get_logger()


class LexMcpClient:
    """MCP client wrapping a long-lived session to the Lex MCP server.

    The session is kept open for the duration of a conversation so the AI
    agent can discover and call Lex tools interactively.

    Usage::

        async with LexMcpClient("https://lex.lab.i.ai.gov.uk/mcp") as client:
            tools = await client.list_tools()
            result = await client.call_tool("search_legislation", {"query": "Housing Act"})
    """

    def __init__(self, url: str) -> None:
        self._url = url
        self._session: ClientSession | None = None
        self._exit_stack: AsyncExitStack | None = None
        self._log = logger.bind(lex_mcp_url=self._url)

    async def connect(self) -> None:
        """Open the MCP session via streamable HTTP transport."""
        if self._session is not None:
            return

        self._log.info("lex_mcp_connecting")
        self._exit_stack = AsyncExitStack()
        try:
            read_stream, write_stream, _ = await self._exit_stack.enter_async_context(
                streamablehttp_client(url=self._url)
            )
            self._session = await self._exit_stack.enter_async_context(
                ClientSession(read_stream, write_stream)
            )
            init_result = await self._session.initialize()
            self._log.info(
                "lex_mcp_connected",
                protocol_version=init_result.protocolVersion,
                server_info=str(init_result.serverInfo),
            )
        except Exception as exc:
            # Clean up partial state on failure
            if self._exit_stack is not None:
                await self._exit_stack.aclose()
                self._exit_stack = None
            self._session = None
            raise LexConnectionError(f"Failed to connect to Lex MCP: {exc}") from exc

    async def disconnect(self) -> None:
        """Close the MCP session."""
        if self._exit_stack is not None:
            self._log.info("lex_mcp_disconnecting")
            await self._exit_stack.aclose()
            self._exit_stack = None
        self._session = None

    async def list_tools(self) -> list[Tool]:
        """Discover available tools on the Lex MCP server."""
        session = self._require_session()
        result = await session.list_tools()
        self._log.debug("lex_mcp_list_tools", count=len(result.tools))
        return list(result.tools)

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> CallToolResult:
        """Execute a Lex MCP tool by name.

        Args:
            name: The tool name (e.g. ``search_legislation``).
            arguments: Tool input arguments as a dict.

        Returns:
            The MCP ``CallToolResult`` containing content blocks.

        Raises:
            LexError: If the tool call returns ``isError=True``.
        """
        session = self._require_session()
        self._log.debug("lex_mcp_call_tool", tool=name)
        result = await session.call_tool(name, arguments)
        if result.isError:
            self._log.warning("lex_mcp_tool_error", tool=name, content=str(result.content))
            raise LexError(f"Lex MCP tool '{name}' returned an error: {result.content}")
        self._log.debug("lex_mcp_tool_ok", tool=name)
        return result

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    async def __aenter__(self) -> LexMcpClient:
        await self.connect()
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.disconnect()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _require_session(self) -> ClientSession:
        if self._session is None:
            raise LexError("MCP session not connected — call connect() first.")
        return self._session
