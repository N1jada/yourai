"""Unit tests for the Lex health manager and failover logic."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from yourai.knowledge.exceptions import LexConnectionError
from yourai.knowledge.lex_health import LexHealthManager
from yourai.knowledge.lex_mcp import LexMcpClient
from yourai.knowledge.lex_rest import LexRestClient


@pytest.fixture
def manager() -> LexHealthManager:
    return LexHealthManager(
        primary_url="http://primary:8080",
        fallback_url="https://fallback.example.com",
        max_failures=3,
    )


# ---------------------------------------------------------------------------
# Initial state
# ---------------------------------------------------------------------------


class TestInitialState:
    def test_starts_on_primary(self, manager: LexHealthManager) -> None:
        assert manager.active_url == "http://primary:8080"
        assert not manager.is_using_fallback
        assert manager.status == "connected"


# ---------------------------------------------------------------------------
# Health check / failover
# ---------------------------------------------------------------------------


class TestHealthCheck:
    async def test_healthy_primary(self, manager: LexHealthManager) -> None:
        """Successful health check keeps primary active."""
        with patch.object(LexRestClient, "health_check", new_callable=AsyncMock) as mock_hc:
            mock_hc.return_value = {"status": "healthy", "collections": 3}
            with patch.object(LexRestClient, "aclose", new_callable=AsyncMock):
                result = await manager.check_health()

        assert result is True
        assert not manager.is_using_fallback
        assert manager.status == "connected"

    async def test_single_failure_no_failover(self, manager: LexHealthManager) -> None:
        """One failure does not trigger failover."""
        with patch.object(
            LexRestClient,
            "health_check",
            new_callable=AsyncMock,
            side_effect=LexConnectionError("refused"),
        ), patch.object(LexRestClient, "aclose", new_callable=AsyncMock):
            result = await manager.check_health()

        assert result is False
        assert not manager.is_using_fallback  # Still on primary

    async def test_failover_after_max_failures(self, manager: LexHealthManager) -> None:
        """After max_failures consecutive failures, switch to fallback."""
        with patch.object(
            LexRestClient,
            "health_check",
            new_callable=AsyncMock,
            side_effect=LexConnectionError("refused"),
        ), patch.object(LexRestClient, "aclose", new_callable=AsyncMock):
            for _ in range(3):
                await manager.check_health()

        assert manager.is_using_fallback
        assert manager.active_url == "https://fallback.example.com"
        assert manager.status == "fallback"

    async def test_recovery_from_fallback(self, manager: LexHealthManager) -> None:
        """When primary recovers, switch back from fallback."""
        # First: trigger failover
        with patch.object(
            LexRestClient,
            "health_check",
            new_callable=AsyncMock,
            side_effect=LexConnectionError("refused"),
        ), patch.object(LexRestClient, "aclose", new_callable=AsyncMock):
            for _ in range(3):
                await manager.check_health()
        assert manager.is_using_fallback

        # Then: primary recovers
        with patch.object(LexRestClient, "health_check", new_callable=AsyncMock) as mock_hc:
            mock_hc.return_value = {"status": "healthy", "collections": 3}
            with patch.object(LexRestClient, "aclose", new_callable=AsyncMock):
                result = await manager.check_health()

        assert result is True
        assert not manager.is_using_fallback
        assert manager.active_url == "http://primary:8080"

    async def test_failures_below_threshold_no_switch(self, manager: LexHealthManager) -> None:
        """Two failures then a success resets the counter without failover."""
        with patch.object(LexRestClient, "aclose", new_callable=AsyncMock):
            # Two failures
            with patch.object(
                LexRestClient,
                "health_check",
                new_callable=AsyncMock,
                side_effect=LexConnectionError("refused"),
            ):
                await manager.check_health()
                await manager.check_health()

            assert not manager.is_using_fallback

            # Then success
            with patch.object(LexRestClient, "health_check", new_callable=AsyncMock) as mock_hc:
                mock_hc.return_value = {"status": "ok", "collections": 5}
                await manager.check_health()

        assert not manager.is_using_fallback
        assert manager._consecutive_failures == 0


# ---------------------------------------------------------------------------
# Client factories
# ---------------------------------------------------------------------------


class TestClientFactories:
    def test_get_rest_client_uses_active_url(self, manager: LexHealthManager) -> None:
        client = manager.get_rest_client()
        assert isinstance(client, LexRestClient)
        assert client._base_url == "http://primary:8080"

    def test_get_rest_client_uses_fallback_after_failover(self, manager: LexHealthManager) -> None:
        manager._using_fallback = True
        client = manager.get_rest_client()
        assert client._base_url == "https://fallback.example.com"

    def test_get_mcp_client_uses_active_url(self, manager: LexHealthManager) -> None:
        client = manager.get_mcp_client()
        assert isinstance(client, LexMcpClient)
        assert client._url == "http://primary:8080/mcp"

    def test_get_mcp_client_uses_fallback_after_failover(self, manager: LexHealthManager) -> None:
        manager._using_fallback = True
        client = manager.get_mcp_client()
        assert client._url == "https://fallback.example.com/mcp"


# ---------------------------------------------------------------------------
# Manual overrides
# ---------------------------------------------------------------------------


class TestManualOverrides:
    def test_force_primary(self, manager: LexHealthManager) -> None:
        manager._using_fallback = True
        manager._consecutive_failures = 5
        manager.force_primary()
        assert not manager.is_using_fallback
        assert manager._consecutive_failures == 0
        assert manager.active_url == "http://primary:8080"
