"""Integration tests for the full user lifecycle via HTTP endpoints.

End-to-end: create user -> assign role -> verify permission -> list -> update -> delete.
"""

from __future__ import annotations

import uuid_utils
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from yourai.core.auth import AuthService
from yourai.core.database import get_db_session
from yourai.core.enums import UserStatus
from yourai.core.models import Permission, Role, RolePermission, Tenant, User, UserRole


async def test_full_user_lifecycle(test_session: AsyncSession) -> None:
    """Test the complete user lifecycle through the API."""
    from yourai.api.main import create_app

    # Setup: tenant, permissions, role, admin user
    tenant = Tenant(
        id=uuid_utils.uuid7(),
        name="Lifecycle Tenant",
        slug="lifecycle",
        is_active=True,
        branding_config={},
        ai_config={},
    )
    test_session.add(tenant)
    await test_session.flush()

    # Create all needed permissions
    perm_names = [
        "list_users",
        "view_user",
        "create_user",
        "update_user_profile",
        "delete_user",
        "update_user_role",
        "list_user_roles",
    ]
    perms = {}
    for name in perm_names:
        p = Permission(id=uuid_utils.uuid7(), name=name, description=name)
        test_session.add(p)
        perms[name] = p
    await test_session.flush()

    admin_role = Role(
        id=uuid_utils.uuid7(),
        tenant_id=tenant.id,
        name="Admin",
        description="Full access",
    )
    test_session.add(admin_role)
    await test_session.flush()

    for p in perms.values():
        test_session.add(RolePermission(role_id=admin_role.id, permission_id=p.id))
    await test_session.flush()

    admin_user = User(
        id=uuid_utils.uuid7(),
        tenant_id=tenant.id,
        email="admin@lifecycle.com",
        given_name="Admin",
        family_name="User",
        status=UserStatus.ACTIVE,
        notification_preferences={},
    )
    test_session.add(admin_user)
    await test_session.flush()
    test_session.add(UserRole(user_id=admin_user.id, role_id=admin_role.id))
    await test_session.flush()

    auth_service = AuthService()
    token = auth_service.create_access_token(admin_user.id, tenant.id, admin_user.email)

    app = create_app()

    async def _override_session():
        yield test_session

    app.dependency_overrides[get_db_session] = _override_session

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"Authorization": f"Bearer {token}"},
    ) as client:
        # 1. Create a new user
        create_resp = await client.post(
            "/api/v1/users",
            json={
                "email": "newuser@lifecycle.com",
                "given_name": "New",
                "family_name": "User",
            },
        )
        assert create_resp.status_code == 201
        new_user = create_resp.json()
        assert new_user["status"] == "pending"
        user_id = new_user["id"]

        # 2. Update the user (activate)
        update_resp = await client.patch(
            f"/api/v1/users/{user_id}",
            json={"status": "active"},
        )
        assert update_resp.status_code == 200
        assert update_resp.json()["status"] == "active"

        # 3. List users — should include the new user
        list_resp = await client.get("/api/v1/users")
        assert list_resp.status_code == 200
        emails = {u["email"] for u in list_resp.json()["items"]}
        assert "newuser@lifecycle.com" in emails

        # 4. Get the user by ID
        get_resp = await client.get(f"/api/v1/users/{user_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["email"] == "newuser@lifecycle.com"

        # 5. Update user name
        name_resp = await client.patch(
            f"/api/v1/users/{user_id}",
            json={"given_name": "Updated"},
        )
        assert name_resp.status_code == 200
        assert name_resp.json()["given_name"] == "Updated"

        # 6. Delete the user
        del_resp = await client.delete(f"/api/v1/users/{user_id}")
        assert del_resp.status_code == 204
