"""Unit tests for the Lex REST client using httpx mock transport."""

from __future__ import annotations

import httpx
import pytest

from yourai.knowledge.exceptions import (
    LexConnectionError,
    LexError,
    LexNotFoundError,
    LexTimeoutError,
)
from yourai.knowledge.lex_rest import (
    Amendment,
    ExplanatoryNote,
    Legislation,
    LegislationFullText,
    LegislationSearchResponse,
    LegislationSection,
    LexRestClient,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_LEGISLATION = {
    "id": "ukpga-1985-68",
    "uri": "/ukpga/1985/68",
    "title": "Housing Act 1985",
    "description": "An Act to consolidate the Housing Acts.",
    "publisher": "Statute Law Database",
    "category": "primary",
    "type": "ukpga",
    "year": 1985,
    "number": 68,
    "status": "revised",
    "number_of_provisions": 625,
    "text": "Some text",
}

SAMPLE_SECTION = {
    "id": "ukpga-1985-68-section-1",
    "uri": "/ukpga/1985/68/section/1",
    "legislation_id": "ukpga-1985-68",
    "number": 1,
    "legislation_type": "ukpga",
    "legislation_year": 1985,
    "legislation_number": 68,
    "title": "Right to buy",
    "text": "A secure tenant has the right to buy.",
}

SAMPLE_AMENDMENT = {
    "id": "amendment-1",
    "changed_legislation": "Housing Act 1985",
    "changed_year": 1985,
    "changed_number": "68",
    "changed_url": "/ukpga/1985/68",
    "affecting_url": "/ukpga/2004/34",
    "affecting_legislation": "Housing Act 2004",
    "type_of_effect": "amended",
}

SAMPLE_EXPLANATORY_NOTE = {
    "id": "en-1",
    "legislation_id": "ukpga-2004-34",
    "text": "This section provides...",
    "route": ["Part 1", "Chapter 1"],
    "order": 1,
    "note_type": "provisions",
}


def _mock_transport(
    responses: dict[str, tuple[int, object]],
) -> httpx.MockTransport:
    """Create a mock transport that routes by URL path."""

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path in responses:
            status, body = responses[path]
            return httpx.Response(status, json=body)
        return httpx.Response(404, json={"detail": "Not found"})

    return httpx.MockTransport(handler)


def _make_client(responses: dict[str, tuple[int, object]]) -> LexRestClient:
    """Create a LexRestClient backed by a mock transport."""
    client = LexRestClient("http://lex-test")
    # Replace the internal httpx client with our mock
    client._client = httpx.AsyncClient(
        transport=_mock_transport(responses),
        base_url="http://lex-test",
    )
    return client


# ---------------------------------------------------------------------------
# Search legislation
# ---------------------------------------------------------------------------


class TestSearchLegislation:
    async def test_search_returns_results(self) -> None:
        response_body = {
            "results": [SAMPLE_LEGISLATION],
            "total": 1,
            "offset": 0,
            "limit": 10,
        }
        client = _make_client({"/legislation/search": (200, response_body)})

        result = await client.search_legislation("Housing Act")
        assert isinstance(result, LegislationSearchResponse)
        assert result.total == 1
        assert len(result.results) == 1
        assert result.results[0]["title"] == "Housing Act 1985"
        await client.aclose()

    async def test_search_with_filters(self) -> None:
        response_body = {"results": [], "total": 0, "offset": 0, "limit": 5}
        client = _make_client({"/legislation/search": (200, response_body)})

        result = await client.search_legislation(
            "test",
            year_from=2000,
            year_to=2020,
            legislation_type=["ukpga"],
            offset=0,
            limit=5,
        )
        assert result.total == 0
        await client.aclose()


# ---------------------------------------------------------------------------
# Lookup legislation
# ---------------------------------------------------------------------------


class TestLookupLegislation:
    async def test_lookup_returns_legislation(self) -> None:
        client = _make_client({"/legislation/lookup": (200, SAMPLE_LEGISLATION)})
        result = await client.lookup_legislation("ukpga", 1985, 68)
        assert isinstance(result, Legislation)
        assert result.title == "Housing Act 1985"
        assert result.year == 1985
        await client.aclose()


# ---------------------------------------------------------------------------
# Legislation sections
# ---------------------------------------------------------------------------


class TestLegislationSections:
    async def test_get_sections(self) -> None:
        client = _make_client({"/legislation/section/lookup": (200, [SAMPLE_SECTION])})
        result = await client.get_legislation_sections("ukpga-1985-68")
        assert len(result) == 1
        assert isinstance(result[0], LegislationSection)
        assert result[0].legislation_id == "ukpga-1985-68"
        await client.aclose()

    async def test_search_sections(self) -> None:
        client = _make_client({"/legislation/section/search": (200, [SAMPLE_SECTION])})
        result = await client.search_legislation_sections("right to buy")
        assert len(result) == 1
        assert result[0].title == "Right to buy"
        await client.aclose()


# ---------------------------------------------------------------------------
# Full text
# ---------------------------------------------------------------------------


class TestLegislationFullText:
    async def test_get_full_text(self) -> None:
        body = {
            "legislation": SAMPLE_LEGISLATION,
            "full_text": "The full text of the Housing Act 1985...",
        }
        client = _make_client({"/legislation/text": (200, body)})
        result = await client.get_legislation_full_text("ukpga-1985-68")
        assert isinstance(result, LegislationFullText)
        assert result.legislation.title == "Housing Act 1985"
        assert "full text" in result.full_text
        await client.aclose()


# ---------------------------------------------------------------------------
# Amendments
# ---------------------------------------------------------------------------


class TestAmendments:
    async def test_search_amendments(self) -> None:
        client = _make_client({"/amendment/search": (200, [SAMPLE_AMENDMENT])})
        result = await client.search_amendments("ukpga-1985-68")
        assert len(result) == 1
        assert isinstance(result[0], Amendment)
        assert result[0].changed_legislation == "Housing Act 1985"
        await client.aclose()

    async def test_search_amendment_sections(self) -> None:
        client = _make_client({"/amendment/section/search": (200, [SAMPLE_AMENDMENT])})
        result = await client.search_amendment_sections("provision-1")
        assert len(result) == 1
        await client.aclose()


# ---------------------------------------------------------------------------
# Explanatory notes
# ---------------------------------------------------------------------------


class TestExplanatoryNotes:
    async def test_search_notes(self) -> None:
        client = _make_client(
            {"/explanatory_note/section/search": (200, [SAMPLE_EXPLANATORY_NOTE])}
        )
        result = await client.search_explanatory_notes(query="housing")
        assert len(result) == 1
        assert isinstance(result[0], ExplanatoryNote)
        assert result[0].note_type == "provisions"
        await client.aclose()

    async def test_get_notes_by_legislation(self) -> None:
        client = _make_client(
            {"/explanatory_note/legislation/lookup": (200, [SAMPLE_EXPLANATORY_NOTE])}
        )
        result = await client.get_explanatory_notes_by_legislation("ukpga-2004-34")
        assert len(result) == 1
        await client.aclose()

    async def test_get_note_by_section(self) -> None:
        client = _make_client({"/explanatory_note/section/lookup": (200, SAMPLE_EXPLANATORY_NOTE)})
        result = await client.get_explanatory_note_by_section("ukpga-2004-34", 1)
        assert isinstance(result, ExplanatoryNote)
        await client.aclose()


# ---------------------------------------------------------------------------
# Utility endpoints
# ---------------------------------------------------------------------------


class TestUtility:
    async def test_health_check(self) -> None:
        client = _make_client({"/healthcheck": (200, {"status": "healthy"})})
        result = await client.health_check()
        assert result["status"] == "healthy"
        await client.aclose()

    async def test_get_stats(self) -> None:
        stats = {"legislation": 5000, "amendments": 12000}
        client = _make_client({"/api/stats": (200, stats)})
        result = await client.get_stats()
        assert result["legislation"] == 5000
        await client.aclose()


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    async def test_404_raises_not_found(self) -> None:
        client = _make_client({})  # all paths return 404
        with pytest.raises(LexNotFoundError):
            await client.health_check()
        await client.aclose()

    async def test_500_raises_lex_error(self) -> None:
        client = _make_client({"/healthcheck": (500, {"error": "internal"})})
        with pytest.raises(LexError, match="500"):
            await client.health_check()
        await client.aclose()

    async def test_connection_error(self) -> None:
        """ConnectError from httpx is wrapped in LexConnectionError."""

        def raise_connect_error(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("Connection refused")

        client = LexRestClient("http://unreachable")
        client._client = httpx.AsyncClient(
            transport=httpx.MockTransport(raise_connect_error),
            base_url="http://unreachable",
        )
        with pytest.raises(LexConnectionError):
            await client.health_check()
        await client.aclose()

    async def test_timeout_error(self) -> None:
        """TimeoutException from httpx is wrapped in LexTimeoutError."""

        def raise_timeout(request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("timed out")

        client = LexRestClient("http://slow")
        client._client = httpx.AsyncClient(
            transport=httpx.MockTransport(raise_timeout),
            base_url="http://slow",
        )
        with pytest.raises(LexTimeoutError):
            await client.health_check()
        await client.aclose()
