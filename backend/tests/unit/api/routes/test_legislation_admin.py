"""Route-level tests for the legislation admin endpoints."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient

from yourai.knowledge.legislation_admin import LegislationAdminService

pytestmark = pytest.mark.anyio


class TestOverviewAuth:
    async def test_requires_auth(self) -> None:
        """Unauthenticated request returns 401."""
        from yourai.api.main import create_app

        app = create_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/admin/legislation/overview")
        assert resp.status_code == 401


class TestOverviewSuccess:
    async def test_overview_returns_200(self) -> None:
        """With auth bypassed, overview returns 200 with health data."""
        from yourai.api.main import create_app
        from yourai.core.middleware import get_current_tenant, get_current_user

        mock_overview = {
            "status": "connected",
            "active_url": "http://primary:8080",
            "primary_url": "http://primary:8080",
            "fallback_url": "https://fallback.example.com",
            "is_using_fallback": False,
            "stats": {"legislation_count": 42},
        }

        app = create_app()

        # Create mock tenant and user
        dummy_tenant = MagicMock()
        dummy_tenant.id = UUID("00000000-0000-0000-0000-000000000001")

        dummy_user = MagicMock()
        dummy_user.id = UUID("00000000-0000-0000-0000-000000000002")
        dummy_user.tenant_id = dummy_tenant.id

        app.dependency_overrides[get_current_tenant] = lambda: dummy_tenant
        app.dependency_overrides[get_current_user] = lambda: dummy_user

        # Also need to mock the PermissionChecker to allow permission
        with (
            patch("yourai.core.roles.PermissionChecker.require", new_callable=AsyncMock),
            patch.object(
                LegislationAdminService,
                "get_overview",
                new_callable=AsyncMock,
                return_value=mock_overview,
            ),
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/admin/legislation/overview")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "connected"
        assert data["stats"]["legislation_count"] == 42


class TestSearchSuccess:
    async def test_search_returns_results(self) -> None:
        """Search endpoint returns paginated results."""
        from yourai.api.main import create_app
        from yourai.core.middleware import get_current_tenant, get_current_user

        mock_result = {
            "results": [{"title": "Housing Act 2004"}],
            "total": 1,
            "offset": 0,
            "limit": 10,
        }

        app = create_app()

        dummy_tenant = MagicMock()
        dummy_tenant.id = UUID("00000000-0000-0000-0000-000000000001")

        dummy_user = MagicMock()
        dummy_user.id = UUID("00000000-0000-0000-0000-000000000002")
        dummy_user.tenant_id = dummy_tenant.id

        app.dependency_overrides[get_current_tenant] = lambda: dummy_tenant
        app.dependency_overrides[get_current_user] = lambda: dummy_user

        with (
            patch("yourai.core.roles.PermissionChecker.require", new_callable=AsyncMock),
            patch.object(
                LegislationAdminService,
                "search",
                new_callable=AsyncMock,
                return_value=mock_result,
            ),
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/v1/admin/legislation/search",
                    json={"query": "housing"},
                )

        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert len(data["results"]) == 1
