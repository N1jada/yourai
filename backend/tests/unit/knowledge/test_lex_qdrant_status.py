"""Unit tests for the LexQdrantStatusClient."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from yourai.knowledge.lex_qdrant_status import (
    LexQdrantStatusClient,
)


@pytest.fixture
def client() -> LexQdrantStatusClient:
    return LexQdrantStatusClient("http://localhost:6333")


class TestIsHealthy:
    async def test_healthy(self, client: LexQdrantStatusClient) -> None:
        """Returns True when Qdrant responds 200."""
        mock_resp = httpx.Response(200)
        with patch.object(client._client, "get", new_callable=AsyncMock, return_value=mock_resp):
            assert await client.is_healthy() is True

    async def test_unhealthy_non_200(self, client: LexQdrantStatusClient) -> None:
        """Returns False when Qdrant responds non-200."""
        mock_resp = httpx.Response(503)
        with patch.object(client._client, "get", new_callable=AsyncMock, return_value=mock_resp):
            assert await client.is_healthy() is False

    async def test_unreachable(self, client: LexQdrantStatusClient) -> None:
        """Returns False when connection fails."""
        with patch.object(
            client._client,
            "get",
            new_callable=AsyncMock,
            side_effect=httpx.ConnectError("Connection refused"),
        ):
            assert await client.is_healthy() is False


class TestListCollections:
    async def test_success(self, client: LexQdrantStatusClient) -> None:
        """Returns parsed collection list."""
        _base = "http://localhost:6333"
        collections_resp = httpx.Response(
            200,
            json={
                "result": {
                    "collections": [
                        {"name": "legislation"},
                        {"name": "caselaw"},
                    ]
                }
            },
            request=httpx.Request("GET", f"{_base}/collections"),
        )
        detail_resp_legislation = httpx.Response(
            200,
            json={
                "result": {
                    "points_count": 5000,
                    "vectors_count": 5000,
                    "indexed_vectors_count": 4900,
                    "status": "green",
                    "optimizer_status": {"status": "ok"},
                    "config": {"disk_data_size": 1024, "ram_data_size": 512},
                }
            },
            request=httpx.Request("GET", f"{_base}/collections/legislation"),
        )
        detail_resp_caselaw = httpx.Response(
            200,
            json={
                "result": {
                    "points_count": 3000,
                    "vectors_count": 3000,
                    "indexed_vectors_count": 3000,
                    "status": "green",
                    "optimizer_status": {"status": "ok"},
                    "config": {},
                }
            },
            request=httpx.Request("GET", f"{_base}/collections/caselaw"),
        )

        call_count = 0

        async def mock_get(url: str, **kwargs: object) -> httpx.Response:
            nonlocal call_count
            if url == "/collections":
                return collections_resp
            if url == "/collections/legislation":
                return detail_resp_legislation
            if url == "/collections/caselaw":
                return detail_resp_caselaw
            raise AssertionError(f"Unexpected URL: {url}")

        with patch.object(client._client, "get", side_effect=mock_get):
            result = await client.list_collections()

        assert len(result) == 2
        assert result[0].name == "legislation"
        assert result[0].points_count == 5000
        assert result[1].name == "caselaw"
        assert result[1].points_count == 3000

    async def test_unreachable(self, client: LexQdrantStatusClient) -> None:
        """Raises when Qdrant is unreachable."""
        with patch.object(
            client._client,
            "get",
            new_callable=AsyncMock,
            side_effect=httpx.ConnectError("Connection refused"),
        ), pytest.raises(httpx.ConnectError):
            await client.list_collections()


class TestGetCollectionDetail:
    async def test_success(self, client: LexQdrantStatusClient) -> None:
        """Returns parsed collection detail."""
        mock_resp = httpx.Response(
            200,
            json={
                "result": {
                    "points_count": 12345,
                    "vectors_count": 12345,
                    "indexed_vectors_count": 12000,
                    "status": "green",
                    "optimizer_status": {"status": "ok"},
                    "config": {"disk_data_size": 2048, "ram_data_size": 1024},
                }
            },
            request=httpx.Request("GET", "http://localhost:6333/collections/legislation"),
        )
        with patch.object(client._client, "get", new_callable=AsyncMock, return_value=mock_resp):
            detail = await client.get_collection_detail("legislation")

        assert detail.name == "legislation"
        assert detail.points_count == 12345
        assert detail.vectors_count == 12345
        assert detail.indexed_vectors_count == 12000
        assert detail.disk_data_size == 2048
        assert detail.ram_data_size == 1024

    async def test_string_optimizer_status(self, client: LexQdrantStatusClient) -> None:
        """Handles Qdrant v1.15+ string optimizer_status without crashing."""
        mock_resp = httpx.Response(
            200,
            json={
                "result": {
                    "points_count": 68,
                    "vectors_count": 68,
                    "indexed_vectors_count": 68,
                    "status": "green",
                    "optimizer_status": "ok",
                    "config": {},
                }
            },
            request=httpx.Request("GET", "http://localhost:6333/collections/legislation"),
        )
        with patch.object(client._client, "get", new_callable=AsyncMock, return_value=mock_resp):
            detail = await client.get_collection_detail("legislation")

        assert detail.name == "legislation"
        assert detail.points_count == 68
        assert detail.status == "ok"

    async def test_not_found(self, client: LexQdrantStatusClient) -> None:
        """Raises on non-existent collection."""
        mock_resp = httpx.Response(404, json={"status": {"error": "not found"}})
        mock_resp.request = httpx.Request("GET", "http://localhost:6333/collections/missing")
        with patch.object(client._client, "get", new_callable=AsyncMock, return_value=mock_resp):
            with pytest.raises(httpx.HTTPStatusError):
                await client.get_collection_detail("missing")
