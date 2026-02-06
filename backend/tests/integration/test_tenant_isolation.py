"""Integration tests for tenant isolation.

Verifies that users in tenant A cannot see data from tenant B,
even when both have valid tokens.
"""

from __future__ import annotations

import uuid_utils
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from yourai.core.auth import AuthService
from yourai.core.database import get_db_session
from yourai.core.enums import UserStatus
from yourai.core.models import Permission, Role, RolePermission, Tenant, User, UserRole
from yourai.core.schemas import CreateUser
from yourai.core.users import UserService


async def test_tenant_a_cannot_see_tenant_b_users(test_session: AsyncSession) -> None:
    """Create users in two tenants and verify cross-tenant isolation."""
    from yourai.api.main import create_app

    # Create two tenants
    tenant_a = Tenant(
        id=uuid_utils.uuid7(),
        name="Tenant A",
        slug="tenant-a",
        is_active=True,
        branding_config={},
        ai_config={},
    )
    tenant_b = Tenant(
        id=uuid_utils.uuid7(),
        name="Tenant B",
        slug="tenant-b",
        is_active=True,
        branding_config={},
        ai_config={},
    )
    test_session.add_all([tenant_a, tenant_b])
    await test_session.flush()

    # Create permissions matching what the routes check for
    perm_list = Permission(id=uuid_utils.uuid7(), name="list_users", description="List users")
    perm_view = Permission(id=uuid_utils.uuid7(), name="view_user", description="View user")
    test_session.add_all([perm_list, perm_view])
    await test_session.flush()

    role_a = Role(
        id=uuid_utils.uuid7(),
        tenant_id=tenant_a.id,
        name="Admin",
        description="Admin",
    )
    role_b = Role(
        id=uuid_utils.uuid7(),
        tenant_id=tenant_b.id,
        name="Admin",
        description="Admin",
    )
    test_session.add_all([role_a, role_b])
    await test_session.flush()

    for p in [perm_list, perm_view]:
        test_session.add(RolePermission(role_id=role_a.id, permission_id=p.id))
        test_session.add(RolePermission(role_id=role_b.id, permission_id=p.id))
    await test_session.flush()

    # Create users in each tenant
    user_a = User(
        id=uuid_utils.uuid7(),
        tenant_id=tenant_a.id,
        email="alice@a.com",
        given_name="Alice",
        family_name="A",
        status=UserStatus.ACTIVE,
        notification_preferences={},
    )
    user_b = User(
        id=uuid_utils.uuid7(),
        tenant_id=tenant_b.id,
        email="bob@b.com",
        given_name="Bob",
        family_name="B",
        status=UserStatus.ACTIVE,
        notification_preferences={},
    )
    test_session.add_all([user_a, user_b])
    await test_session.flush()

    test_session.add(UserRole(user_id=user_a.id, role_id=role_a.id))
    test_session.add(UserRole(user_id=user_b.id, role_id=role_b.id))
    await test_session.flush()

    # Create additional users in each tenant for list verification
    svc = UserService(test_session)
    await svc.create_user(
        tenant_a.id, CreateUser(email="extra-a@a.com", given_name="Extra", family_name="A")
    )
    await svc.create_user(
        tenant_b.id, CreateUser(email="extra-b@b.com", given_name="Extra", family_name="B")
    )

    auth_service = AuthService()

    # Token for user A
    token_a = auth_service.create_access_token(user_a.id, tenant_a.id, user_a.email)

    app = create_app()

    async def _override_session():
        yield test_session

    app.dependency_overrides[get_db_session] = _override_session

    transport = ASGITransport(app=app)

    # User A lists users — should only see users from tenant A
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"Authorization": f"Bearer {token_a}"},
    ) as client_a:
        response = await client_a.get("/api/v1/users")
        assert response.status_code == 200
        data = response.json()
        emails = {u["email"] for u in data["items"]}
        assert "alice@a.com" in emails or "extra-a@a.com" in emails
        # Tenant B users should NOT appear
        assert "bob@b.com" not in emails
        assert "extra-b@b.com" not in emails

    # User A cannot access user B by ID
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"Authorization": f"Bearer {token_a}"},
    ) as client_a:
        response = await client_a.get(f"/api/v1/users/{user_b.id}")
        # Should get 404 because user B is in a different tenant
        assert response.status_code == 403 or response.status_code == 404
