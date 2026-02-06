"""Unit tests for the Lex MCP client with mocked session."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from yourai.knowledge.exceptions import LexConnectionError, LexError
from yourai.knowledge.lex_mcp import LexMcpClient

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_tool(name: str, description: str = "") -> MagicMock:
    tool = MagicMock()
    tool.name = name
    tool.description = description
    return tool


def _mock_call_result(content: list[object], *, is_error: bool = False) -> MagicMock:
    result = MagicMock()
    result.content = content
    result.isError = is_error
    return result


# ---------------------------------------------------------------------------
# Connection lifecycle
# ---------------------------------------------------------------------------


class TestConnection:
    async def test_connect_and_disconnect(self) -> None:
        """connect() sets up the session; disconnect() tears it down."""
        client = LexMcpClient("http://lex-test/mcp")

        mock_init_result = MagicMock()
        mock_init_result.protocolVersion = "2025-03-26"
        mock_init_result.serverInfo = "lex-test"

        mock_session = AsyncMock()
        mock_session.initialize = AsyncMock(return_value=mock_init_result)

        with (
            patch(
                "yourai.knowledge.lex_mcp.streamablehttp_client",
            ) as mock_transport,
            patch(
                "yourai.knowledge.lex_mcp.ClientSession",
            ) as mock_session_cls,
        ):
            # streamablehttp_client is an async context manager yielding a 3-tuple
            mock_cm = AsyncMock()
            mock_cm.__aenter__ = AsyncMock(return_value=(AsyncMock(), AsyncMock(), MagicMock()))
            mock_cm.__aexit__ = AsyncMock(return_value=False)
            mock_transport.return_value = mock_cm

            # ClientSession is also an async context manager
            mock_session_cm = AsyncMock()
            mock_session_cm.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_cm.__aexit__ = AsyncMock(return_value=False)
            mock_session_cls.return_value = mock_session_cm

            await client.connect()
            assert client._session is not None

            await client.disconnect()
            assert client._session is None

    async def test_connect_failure_raises(self) -> None:
        """Connection failure is wrapped in LexConnectionError."""
        client = LexMcpClient("http://unreachable/mcp")

        with patch(
            "yourai.knowledge.lex_mcp.streamablehttp_client",
        ) as mock_transport:
            mock_cm = AsyncMock()
            mock_cm.__aenter__ = AsyncMock(side_effect=OSError("refused"))
            mock_cm.__aexit__ = AsyncMock(return_value=False)
            mock_transport.return_value = mock_cm

            with pytest.raises(LexConnectionError, match="refused"):
                await client.connect()

        assert client._session is None

    async def test_context_manager(self) -> None:
        """async with LexMcpClient() connects and disconnects."""
        mock_init_result = MagicMock()
        mock_init_result.protocolVersion = "2025-03-26"
        mock_init_result.serverInfo = "lex-test"

        mock_session = AsyncMock()
        mock_session.initialize = AsyncMock(return_value=mock_init_result)

        with (
            patch(
                "yourai.knowledge.lex_mcp.streamablehttp_client",
            ) as mock_transport,
            patch(
                "yourai.knowledge.lex_mcp.ClientSession",
            ) as mock_session_cls,
        ):
            mock_cm = AsyncMock()
            mock_cm.__aenter__ = AsyncMock(return_value=(AsyncMock(), AsyncMock(), MagicMock()))
            mock_cm.__aexit__ = AsyncMock(return_value=False)
            mock_transport.return_value = mock_cm

            mock_session_cm = AsyncMock()
            mock_session_cm.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_cm.__aexit__ = AsyncMock(return_value=False)
            mock_session_cls.return_value = mock_session_cm

            async with LexMcpClient("http://lex-test/mcp") as client:
                assert client._session is not None
            # After exit, session should be None
            assert client._session is None


# ---------------------------------------------------------------------------
# Tool operations
# ---------------------------------------------------------------------------


class TestToolOperations:
    @pytest.fixture
    def connected_client(self) -> LexMcpClient:
        """A client with a mocked session already connected."""
        client = LexMcpClient("http://lex-test/mcp")
        client._session = AsyncMock()
        return client

    async def test_list_tools(self, connected_client: LexMcpClient) -> None:
        tools = [_mock_tool("search_legislation"), _mock_tool("get_case_law")]
        mock_result = MagicMock()
        mock_result.tools = tools
        connected_client._session.list_tools = AsyncMock(return_value=mock_result)

        result = await connected_client.list_tools()
        assert len(result) == 2
        assert result[0].name == "search_legislation"

    async def test_call_tool_success(self, connected_client: LexMcpClient) -> None:
        call_result = _mock_call_result(["some content"], is_error=False)
        connected_client._session.call_tool = AsyncMock(return_value=call_result)

        result = await connected_client.call_tool("search_legislation", {"query": "Housing"})
        assert result.content == ["some content"]
        assert not result.isError

    async def test_call_tool_error_raises(self, connected_client: LexMcpClient) -> None:
        call_result = _mock_call_result(["error detail"], is_error=True)
        connected_client._session.call_tool = AsyncMock(return_value=call_result)

        with pytest.raises(LexError, match="returned an error"):
            await connected_client.call_tool("bad_tool", {})

    async def test_call_tool_without_session_raises(self) -> None:
        client = LexMcpClient("http://lex-test/mcp")
        with pytest.raises(LexError, match="not connected"):
            await client.call_tool("search_legislation", {"query": "test"})

    async def test_list_tools_without_session_raises(self) -> None:
        client = LexMcpClient("http://lex-test/mcp")
        with pytest.raises(LexError, match="not connected"):
            await client.list_tools()
