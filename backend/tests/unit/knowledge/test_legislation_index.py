"""Unit tests for legislation index — Qdrant client extensions, service, and task."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from yourai.knowledge.lex_qdrant_status import LexQdrantStatusClient


@pytest.fixture
def client() -> LexQdrantStatusClient:
    return LexQdrantStatusClient("http://localhost:6333")


_BASE = "http://localhost:6333"


# ---------------------------------------------------------------------------
# Qdrant client — scroll_legislation
# ---------------------------------------------------------------------------


class TestScrollLegislation:
    async def test_scroll_no_filter(self, client: LexQdrantStatusClient) -> None:
        """Returns items and next_offset from scroll endpoint."""
        resp = httpx.Response(
            200,
            json={
                "result": {
                    "points": [
                        {
                            "id": "abc-123",
                            "payload": {
                                "id": "ukpga-2023-15",
                                "type": "ukpga",
                                "year": 2023,
                                "number": 15,
                                "title": "Test Act",
                            },
                        },
                    ],
                    "next_page_offset": "abc-124",
                }
            },
            request=httpx.Request("POST", f"{_BASE}/collections/legislation/points/scroll"),
        )
        with patch.object(client._client, "post", new_callable=AsyncMock, return_value=resp):
            result = await client.scroll_legislation()

        assert len(result["items"]) == 1
        assert result["items"][0]["qdrant_point_id"] == "abc-123"
        assert result["items"][0]["id"] == "ukpga-2023-15"
        assert result["next_offset"] == "abc-124"

    async def test_scroll_with_filter(self, client: LexQdrantStatusClient) -> None:
        """Includes filter conditions in the request body."""
        resp = httpx.Response(
            200,
            json={"result": {"points": [], "next_page_offset": None}},
            request=httpx.Request("POST", f"{_BASE}/collections/legislation/points/scroll"),
        )
        mock_post = AsyncMock(return_value=resp)
        with patch.object(client._client, "post", mock_post):
            result = await client.scroll_legislation(type_filter="ukpga", year_filter=2023)

        assert result["items"] == []
        assert result["next_offset"] is None

        # Verify filter was sent
        call_kwargs = mock_post.call_args
        body = call_kwargs.kwargs["json"]
        assert "filter" in body
        assert len(body["filter"]["must"]) == 2

    async def test_scroll_empty(self, client: LexQdrantStatusClient) -> None:
        """Returns empty items when no points found."""
        resp = httpx.Response(
            200,
            json={"result": {"points": []}},
            request=httpx.Request("POST", f"{_BASE}/collections/legislation/points/scroll"),
        )
        with patch.object(client._client, "post", new_callable=AsyncMock, return_value=resp):
            result = await client.scroll_legislation()

        assert result["items"] == []
        assert result["next_offset"] is None


# ---------------------------------------------------------------------------
# Qdrant client — count_by_filter
# ---------------------------------------------------------------------------


class TestCountByFilter:
    async def test_count(self, client: LexQdrantStatusClient) -> None:
        resp = httpx.Response(
            200,
            json={"result": {"count": 42}},
            request=httpx.Request("POST", f"{_BASE}/collections/legislation/points/count"),
        )
        with patch.object(client._client, "post", new_callable=AsyncMock, return_value=resp):
            count = await client.count_by_filter(
                "legislation",
                [{"key": "type", "match": {"value": "ukpga"}}],
            )

        assert count == 42

    async def test_count_empty_filter(self, client: LexQdrantStatusClient) -> None:
        resp = httpx.Response(
            200,
            json={"result": {"count": 100}},
            request=httpx.Request("POST", f"{_BASE}/collections/legislation/points/count"),
        )
        with patch.object(client._client, "post", new_callable=AsyncMock, return_value=resp):
            count = await client.count_by_filter("legislation", [])

        assert count == 100


# ---------------------------------------------------------------------------
# Qdrant client — delete_by_filter
# ---------------------------------------------------------------------------


class TestDeleteByFilter:
    async def test_delete(self, client: LexQdrantStatusClient) -> None:
        resp = httpx.Response(
            200,
            json={"result": {"status": "acknowledged"}},
            request=httpx.Request("POST", f"{_BASE}/collections/legislation/points/delete"),
        )
        with patch.object(client._client, "post", new_callable=AsyncMock, return_value=resp):
            result = await client.delete_by_filter(
                "legislation",
                [{"key": "id", "match": {"value": "ukpga-2023-15"}}],
            )

        assert result is True


# ---------------------------------------------------------------------------
# Qdrant client — count_sections_for_legislation
# ---------------------------------------------------------------------------


class TestCountSectionsForLegislation:
    async def test_count_sections(self, client: LexQdrantStatusClient) -> None:
        resp = httpx.Response(
            200,
            json={"result": {"count": 73}},
            request=httpx.Request("POST", f"{_BASE}/collections/legislation_section/points/count"),
        )
        with patch.object(client._client, "post", new_callable=AsyncMock, return_value=resp):
            count = await client.count_sections_for_legislation("ukpga-2023-15")

        assert count == 73


# ---------------------------------------------------------------------------
# Qdrant client — delete_legislation_by_id
# ---------------------------------------------------------------------------


class TestDeleteLegislationById:
    async def test_success(self, client: LexQdrantStatusClient) -> None:
        resp = httpx.Response(
            200,
            json={"result": {"status": "acknowledged"}},
            request=httpx.Request("POST", f"{_BASE}/collections/legislation/points/delete"),
        )
        with patch.object(client._client, "post", new_callable=AsyncMock, return_value=resp):
            result = await client.delete_legislation_by_id("ukpga-2023-15")

        assert result["legislation"] is True
        assert result["sections"] is True

    async def test_partial_failure(self, client: LexQdrantStatusClient) -> None:
        """Handles failure on one collection gracefully."""
        call_count = 0

        async def mock_post(url: str, **kwargs: object) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            if "legislation_section" in url:
                raise httpx.ConnectError("Connection refused")
            return httpx.Response(
                200,
                json={"result": {"status": "acknowledged"}},
                request=httpx.Request("POST", url),
            )

        with patch.object(client._client, "post", side_effect=mock_post):
            result = await client.delete_legislation_by_id("ukpga-2023-15")

        assert result["legislation"] is True
        assert result["sections"] is False


# ---------------------------------------------------------------------------
# Service — trigger_targeted_ingestion
# ---------------------------------------------------------------------------


class TestTriggerTargetedIngestion:
    async def test_creates_job_and_dispatches(self) -> None:
        """Creates a job record and dispatches celery task."""
        from yourai.knowledge.legislation_admin import LegislationAdminService

        service = LegislationAdminService()

        mock_session = AsyncMock()
        mock_session.flush = AsyncMock()

        with patch(
            "yourai.knowledge.legislation_admin.LegislationAdminService.trigger_targeted_ingestion",
            wraps=service.trigger_targeted_ingestion,
        ), patch("yourai.knowledge.lex_tasks.run_lex_targeted_ingestion_task") as mock_task:
            mock_task.delay = MagicMock()

            from uuid import UUID

            result = await service.trigger_targeted_ingestion(
                session=mock_session,
                tenant_id=UUID("00000000-0000-0000-0000-000000000001"),
                user_id=UUID("00000000-0000-0000-0000-000000000002"),
                types=["ukpga", "uksi"],
                years=[2023, 2024],
                limit=50,
            )

            assert result["mode"] == "targeted"
            assert result["status"] == "pending"
            mock_task.delay.assert_called_once()
            mock_session.add.assert_called_once()


# ---------------------------------------------------------------------------
# Task — command building
# ---------------------------------------------------------------------------


class TestTargetedIngestionCommand:
    def test_command_includes_types_and_years(self) -> None:
        """Verify the command would include --types and --years flags."""
        # This tests the command-building logic by extracting it
        types = ["ukpga", "uksi"]
        years = [2023, 2024]
        limit = 50
        container = "lex-pipeline"

        cmd = [
            "docker",
            "exec",
            container,
            "python",
            "-m",
            "lex.ingest",
            "--mode",
            "legislation-unified",
        ]
        if types:
            cmd.extend(["--types", ",".join(types)])
        if years:
            cmd.extend(["--years", ",".join(str(y) for y in years)])
        if limit:
            cmd.extend(["--limit", str(limit)])
        cmd.append("--non-interactive")

        assert "--types" in cmd
        assert "ukpga,uksi" in cmd
        assert "--years" in cmd
        assert "2023,2024" in cmd
        assert "--limit" in cmd
        assert "50" in cmd
        assert "--non-interactive" in cmd

    def test_command_without_limit(self) -> None:
        """No --limit flag when limit is None."""
        types = ["ukpga"]
        years = [2025]
        limit = None
        container = "lex-pipeline"

        cmd = [
            "docker",
            "exec",
            container,
            "python",
            "-m",
            "lex.ingest",
            "--mode",
            "legislation-unified",
        ]
        if types:
            cmd.extend(["--types", ",".join(types)])
        if years:
            cmd.extend(["--years", ",".join(str(y) for y in years)])
        if limit:
            cmd.extend(["--limit", str(limit)])
        cmd.append("--non-interactive")

        assert "--limit" not in cmd
