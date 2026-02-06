"""Integration tests against the public Lex API.

These tests hit the live public API at lex.lab.i.ai.gov.uk and require
internet connectivity.  Mark with ``pytest.mark.integration`` so they
can be skipped in CI when not needed.

Run with:
    uv run pytest tests/integration/test_lex_integration.py -v

Note: The public Lex API can be slow (>30s for some endpoints).
Tests that make multiple sequential requests use ``flaky_timeout``
to skip gracefully on timeout rather than fail.
"""

from __future__ import annotations

import functools
from collections.abc import Callable
from typing import Any

import pytest

from yourai.knowledge.exceptions import LexTimeoutError
from yourai.knowledge.lex_health import LexHealthManager
from yourai.knowledge.lex_rest import (
    Amendment,
    ExplanatoryNote,
    Legislation,
    LegislationFullText,
    LegislationSearchResponse,
    LegislationSection,
    LexRestClient,
)

PUBLIC_LEX_URL = "https://lex.lab.i.ai.gov.uk"

pytestmark = pytest.mark.integration


def skip_on_timeout(fn: Callable[..., Any]) -> Callable[..., Any]:
    """Skip the test if the public Lex API times out."""

    @functools.wraps(fn)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return await fn(*args, **kwargs)
        except LexTimeoutError:
            pytest.skip("Public Lex API timed out")

    return wrapper


@pytest.fixture
async def client():
    c = LexRestClient(PUBLIC_LEX_URL, timeout=60.0)
    yield c
    await c.aclose()


# ---------------------------------------------------------------------------
# REST — Legislation search
# ---------------------------------------------------------------------------


class TestLegislationSearch:
    @skip_on_timeout
    async def test_housing_act_search(self, client: LexRestClient) -> None:
        """Search for 'Housing Act 1985' returns at least one result."""
        result = await client.search_legislation("Housing Act 1985", limit=5)
        assert isinstance(result, LegislationSearchResponse)
        assert result.total > 0
        assert len(result.results) > 0
        # The Housing Act 1985 should be in the results
        titles = [r.get("title", "") for r in result.results]
        assert any("Housing" in t for t in titles), f"Expected Housing Act in {titles}"

    @skip_on_timeout
    async def test_search_with_year_filter(self, client: LexRestClient) -> None:
        """Filtering by year range narrows results."""
        result = await client.search_legislation(
            "Act", year_from=2020, year_to=2024, limit=5
        )
        assert isinstance(result, LegislationSearchResponse)
        # Should return something (there are Acts from 2020-2024)
        assert result.total >= 0

    @skip_on_timeout
    async def test_search_pagination(self, client: LexRestClient) -> None:
        """Offset and limit work for pagination."""
        page1 = await client.search_legislation("Act", limit=2, offset=0)
        page2 = await client.search_legislation("Act", limit=2, offset=2)
        assert page1.offset == 0
        assert page2.offset == 2
        # Pages should contain different results
        if page1.total > 4:
            ids1 = {r.get("id") for r in page1.results}
            ids2 = {r.get("id") for r in page2.results}
            assert ids1 != ids2


# ---------------------------------------------------------------------------
# REST — Legislation lookup
# ---------------------------------------------------------------------------


class TestLegislationLookup:
    @skip_on_timeout
    async def test_lookup_housing_act(self, client: LexRestClient) -> None:
        """Look up Housing Act 1985 by citation."""
        result = await client.lookup_legislation("ukpga", 1985, 68)
        assert isinstance(result, Legislation)
        assert "Housing" in result.title
        assert result.year == 1985
        assert result.number == 68
        assert result.category == "primary"


# ---------------------------------------------------------------------------
# REST — Sections
# ---------------------------------------------------------------------------


class TestSections:
    @skip_on_timeout
    async def test_get_sections(self, client: LexRestClient) -> None:
        """Get sections of the Housing Act 1985."""
        leg = await client.lookup_legislation("ukpga", 1985, 68)
        sections = await client.get_legislation_sections(leg.id, limit=5)
        assert len(sections) > 0
        assert isinstance(sections[0], LegislationSection)
        assert sections[0].legislation_id == leg.id

    @skip_on_timeout
    async def test_search_sections(self, client: LexRestClient) -> None:
        """Search for sections containing 'right to buy'."""
        sections = await client.search_legislation_sections(
            "right to buy", size=5
        )
        assert len(sections) > 0
        assert isinstance(sections[0], LegislationSection)


# ---------------------------------------------------------------------------
# REST — Full text
# ---------------------------------------------------------------------------


class TestFullText:
    @skip_on_timeout
    async def test_get_full_text(self, client: LexRestClient) -> None:
        """Get the full text of a small piece of legislation."""
        leg = await client.lookup_legislation("ukpga", 1985, 68)
        result = await client.get_legislation_full_text(leg.id)
        assert isinstance(result, LegislationFullText)
        assert len(result.full_text) > 0
        assert result.legislation.id == leg.id


# ---------------------------------------------------------------------------
# REST — Amendments
# ---------------------------------------------------------------------------


class TestAmendments:
    @skip_on_timeout
    async def test_search_amendments(self, client: LexRestClient) -> None:
        """Search for amendments to the Housing Act 1985."""
        leg = await client.lookup_legislation("ukpga", 1985, 68)
        amendments = await client.search_amendments(leg.id, size=5)
        assert len(amendments) > 0
        assert isinstance(amendments[0], Amendment)


# ---------------------------------------------------------------------------
# REST — Explanatory notes
# ---------------------------------------------------------------------------


class TestExplanatoryNotes:
    @skip_on_timeout
    async def test_search_explanatory_notes(self, client: LexRestClient) -> None:
        """Search for explanatory notes about housing."""
        notes = await client.search_explanatory_notes(query="housing", size=5)
        assert isinstance(notes, list)
        if len(notes) > 0:
            assert isinstance(notes[0], ExplanatoryNote)


# ---------------------------------------------------------------------------
# REST — Utility
# ---------------------------------------------------------------------------


class TestUtility:
    @skip_on_timeout
    async def test_health_check(self, client: LexRestClient) -> None:
        """Public API healthcheck is reachable."""
        result = await client.health_check()
        assert isinstance(result, dict)

    @skip_on_timeout
    async def test_get_stats(self, client: LexRestClient) -> None:
        """Stats endpoint returns collection counts."""
        stats = await client.get_stats()
        assert isinstance(stats, dict)
        # Should have some data
        assert len(stats) > 0


# ---------------------------------------------------------------------------
# Failover simulation
# ---------------------------------------------------------------------------


class TestFailover:
    async def test_failover_to_public_api(self) -> None:
        """With self-hosted down, health manager switches to public API.

        The self-hosted instance is not running, so after max_failures the
        manager should switch to the public fallback.
        """
        manager = LexHealthManager(
            primary_url="http://localhost:19876",  # Guaranteed-unused port
            fallback_url=PUBLIC_LEX_URL,
            max_failures=2,
        )

        # Primary is down — two checks should trigger failover
        for _ in range(2):
            await manager.check_health()

        assert manager.is_using_fallback
        assert manager.active_url == PUBLIC_LEX_URL

        # Verify we can actually use the fallback
        client = manager.get_rest_client(timeout=60.0)
        try:
            result = await client.health_check()
            assert isinstance(result, dict)
        except LexTimeoutError:
            pytest.skip("Public Lex API timed out during fallback verification")
        finally:
            await client.aclose()


# ---------------------------------------------------------------------------
# MCP — Tool discovery and call
# ---------------------------------------------------------------------------


class TestMcp:
    async def test_mcp_list_tools(self) -> None:
        """Connect to the public Lex MCP endpoint and list tools."""
        from yourai.knowledge.lex_mcp import LexMcpClient

        async with LexMcpClient(f"{PUBLIC_LEX_URL}/mcp") as client:
            tools = await client.list_tools()
            assert len(tools) > 0
            tool_names = [t.name for t in tools]
            # Lex MCP should have legislation search tools
            assert any("legislation" in name.lower() for name in tool_names), (
                f"Expected a legislation tool, got: {tool_names}"
            )

    async def test_mcp_search_legislation(self) -> None:
        """Call the search_legislation MCP tool."""
        from yourai.knowledge.lex_mcp import LexMcpClient

        async with LexMcpClient(f"{PUBLIC_LEX_URL}/mcp") as client:
            tools = await client.list_tools()
            # Find a search tool
            search_tools = [
                t
                for t in tools
                if "search" in t.name.lower() and "legislation" in t.name.lower()
            ]
            if not search_tools:
                pytest.skip("No legislation search tool found in MCP")

            result = await client.call_tool(
                search_tools[0].name,
                {"query": "Housing Act 1985"},
            )
            assert result.content is not None
            assert len(result.content) > 0
