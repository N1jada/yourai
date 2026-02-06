"""Integration tests for the auth flow via HTTP endpoints.

Tests the full request pipeline: token -> middleware -> route -> response.
"""

from __future__ import annotations

from httpx import AsyncClient


async def test_get_me_with_valid_token(async_client: AsyncClient) -> None:
    """GET /users/me with a valid token returns 200 and user data."""
    response = await async_client.get("/api/v1/users/me")
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["status"] == "active"


async def test_get_me_without_token() -> None:
    """GET /users/me without a token returns 401."""
    from httpx import ASGITransport
    from httpx import AsyncClient as AC

    from yourai.api.main import create_app

    app = create_app()
    transport = ASGITransport(app=app)
    async with AC(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/users/me")
        assert response.status_code == 401


async def test_get_me_with_invalid_token() -> None:
    """GET /users/me with an invalid token returns 401."""
    from httpx import ASGITransport
    from httpx import AsyncClient as AC

    from yourai.api.main import create_app

    app = create_app()
    transport = ASGITransport(app=app)
    async with AC(
        transport=transport,
        base_url="http://test",
        headers={"Authorization": "Bearer invalid-token"},
    ) as client:
        response = await client.get("/api/v1/users/me")
        assert response.status_code == 401
