"""Unit tests for the LegislationAdminService."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from yourai.knowledge.exceptions import LexConnectionError
from yourai.knowledge.legislation_admin import LegislationAdminService
from yourai.knowledge.lex_health import LexHealthManager
from yourai.knowledge.lex_rest import (
    Amendment,
    Legislation,
    LegislationCategory,
    LegislationSearchResponse,
    LegislationSection,
    LegislationType,
    LexRestClient,
    ProvisionType,
)


@pytest.fixture
def manager() -> LexHealthManager:
    return LexHealthManager(
        primary_url="http://primary:8080",
        fallback_url="https://fallback.example.com",
    )


@pytest.fixture
def service(manager: LexHealthManager) -> LegislationAdminService:
    return LegislationAdminService(health_manager=manager)


# ---------------------------------------------------------------------------
# Overview
# ---------------------------------------------------------------------------


class TestGetOverview:
    async def test_healthy(self, service: LegislationAdminService) -> None:
        """Returns status + stats when Lex is reachable."""
        mock_stats = {"legislation_count": 42, "sections_count": 1200}

        with (
            patch.object(
                LexRestClient, "get_stats", new_callable=AsyncMock, return_value=mock_stats
            ),
            patch.object(LexRestClient, "aclose", new_callable=AsyncMock),
        ):
            result = await service.get_overview()

        assert result["status"] == "connected"
        assert result["stats"] == mock_stats
        assert result["active_url"] == "http://primary:8080"
        assert result["is_using_fallback"] is False

    async def test_lex_unreachable(self, service: LegislationAdminService) -> None:
        """Returns stats=None when Lex is not reachable."""
        with (
            patch.object(
                LexRestClient,
                "get_stats",
                new_callable=AsyncMock,
                side_effect=LexConnectionError("refused"),
            ),
            patch.object(LexRestClient, "aclose", new_callable=AsyncMock),
        ):
            result = await service.get_overview()

        assert result["stats"] is None
        assert result["status"] == "connected"  # status reflects failover, not stats


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------


class TestSearch:
    async def test_forwards_params(self, service: LegislationAdminService) -> None:
        """Verifies search parameters are forwarded to the REST client."""
        mock_response = LegislationSearchResponse(
            results=[{"title": "Housing Act 2004"}],
            total=1,
            offset=0,
            limit=10,
        )

        with (
            patch.object(
                LexRestClient,
                "search_legislation",
                new_callable=AsyncMock,
                return_value=mock_response,
            ) as mock_search,
            patch.object(LexRestClient, "aclose", new_callable=AsyncMock),
        ):
            result = await service.search(
                query="housing",
                year_from=2000,
                year_to=2024,
                legislation_type=["ukpga"],
                offset=0,
                limit=10,
            )

        mock_search.assert_called_once_with(
            "housing",
            year_from=2000,
            year_to=2024,
            legislation_type=["ukpga"],
            offset=0,
            limit=10,
            include_text=False,
        )
        assert result["total"] == 1
        assert len(result["results"]) == 1


# ---------------------------------------------------------------------------
# Detail
# ---------------------------------------------------------------------------


class TestGetDetail:
    async def test_aggregates(self, service: LegislationAdminService) -> None:
        """Combines legislation lookup, sections, and amendments."""
        mock_legislation = Legislation(
            id="leg-1",
            uri="/ukpga/2004/34",
            title="Housing Act 2004",
            description="An Act to make provision about housing conditions.",
            publisher="TSO",
            category=LegislationCategory.PRIMARY,
            type=LegislationType.UKPGA,
            year=2004,
            number=34,
            status="current",
            number_of_provisions=270,
        )
        mock_sections = [
            LegislationSection(
                id="sec-1",
                uri="/ukpga/2004/34/section/1",
                legislation_id="leg-1",
                number=1,
                legislation_type=LegislationType.UKPGA,
                legislation_year=2004,
                legislation_number=34,
                title="Meaning of housing",
                provision_type=ProvisionType.SECTION,
            )
        ]
        mock_amendments = [
            Amendment(
                id="amd-1",
                changed_legislation="Housing Act 2004",
                changed_year=2004,
                changed_number="34",
                changed_url="/ukpga/2004/34",
                affecting_url="/ukpga/2016/22",
            )
        ]

        with (
            patch.object(
                LexRestClient,
                "lookup_legislation",
                new_callable=AsyncMock,
                return_value=mock_legislation,
            ),
            patch.object(
                LexRestClient,
                "get_legislation_sections",
                new_callable=AsyncMock,
                return_value=mock_sections,
            ),
            patch.object(
                LexRestClient,
                "search_amendments",
                new_callable=AsyncMock,
                return_value=mock_amendments,
            ),
            patch.object(LexRestClient, "aclose", new_callable=AsyncMock),
        ):
            result = await service.get_detail("ukpga", 2004, 34)

        assert result["legislation"]["title"] == "Housing Act 2004"
        assert len(result["sections"]) == 1
        assert len(result["amendments"]) == 1


# ---------------------------------------------------------------------------
# Health management
# ---------------------------------------------------------------------------


class TestHealthManagement:
    async def test_check_health(self, service: LegislationAdminService) -> None:
        with (
            patch.object(LexRestClient, "health_check", new_callable=AsyncMock) as mock_hc,
            patch.object(LexRestClient, "aclose", new_callable=AsyncMock),
        ):
            mock_hc.return_value = {"status": "healthy", "collections": 3}
            result = await service.check_health()

        assert result["primary_healthy"] is True
        assert result["status"] == "connected"

    def test_force_primary(self, service: LegislationAdminService) -> None:
        service._health._using_fallback = True
        result = service.force_primary()
        assert result["status"] == "connected"
        assert not service._health.is_using_fallback
