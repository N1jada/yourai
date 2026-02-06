"""Unit tests for RoleService and PermissionChecker."""

from __future__ import annotations

from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from yourai.core.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from yourai.core.models import Permission, Role, Tenant, User
from yourai.core.roles import PermissionChecker, RoleService
from yourai.core.schemas import CreateRole, UpdateRole


async def test_create_role(
    test_session: AsyncSession,
    sample_tenant: Tenant,
) -> None:
    """Creating a role returns a RoleResponse."""
    svc = RoleService(test_session)
    data = CreateRole(name="Editor", description="Can edit content")
    role = await svc.create_role(sample_tenant.id, data)
    assert role.name == "Editor"
    assert str(role.tenant_id) == str(sample_tenant.id)


async def test_create_role_duplicate_name_raises_conflict(
    test_session: AsyncSession,
    sample_tenant: Tenant,
) -> None:
    """Creating a role with a duplicate name raises ConflictError."""
    svc = RoleService(test_session)
    data = CreateRole(name="DupRole")
    await svc.create_role(sample_tenant.id, data)

    with pytest.raises(ConflictError):
        await svc.create_role(sample_tenant.id, data)


async def test_create_role_with_permissions(
    test_session: AsyncSession,
    sample_tenant: Tenant,
    sample_permission: Permission,
) -> None:
    """Creating a role with permission_ids attaches those permissions."""
    svc = RoleService(test_session)
    data = CreateRole(
        name="WithPerms",
        permission_ids=[UUID(str(sample_permission.id))],
    )
    role = await svc.create_role(sample_tenant.id, data)
    assert len(role.permissions) == 1
    assert role.permissions[0].name == "list_users"


async def test_update_role_name(
    test_session: AsyncSession,
    sample_tenant: Tenant,
) -> None:
    """Updating a role's name succeeds."""
    svc = RoleService(test_session)
    role = await svc.create_role(sample_tenant.id, CreateRole(name="OldName"))
    updated = await svc.update_role(role.id, sample_tenant.id, UpdateRole(name="NewName"))
    assert updated.name == "NewName"


async def test_delete_role(
    test_session: AsyncSession,
    sample_tenant: Tenant,
) -> None:
    """Deleting a role removes it."""
    svc = RoleService(test_session)
    role = await svc.create_role(sample_tenant.id, CreateRole(name="ToDelete"))
    await svc.delete_role(role.id, sample_tenant.id)

    with pytest.raises(NotFoundError):
        await svc.get_role(role.id, sample_tenant.id)


async def test_list_roles(
    test_session: AsyncSession,
    sample_tenant: Tenant,
    sample_role: Role,
) -> None:
    """Listing roles returns all roles for the tenant."""
    svc = RoleService(test_session)
    roles = await svc.list_roles(sample_tenant.id)
    assert len(roles) >= 1
    names = {r.name for r in roles}
    assert "Admin" in names


async def test_permission_checker_has_permission(
    test_session: AsyncSession,
    sample_user: User,
) -> None:
    """PermissionChecker.check returns True when user has the permission."""
    checker = PermissionChecker(test_session)
    result = await checker.check(sample_user.id, "list_users")
    assert result is True


async def test_permission_checker_lacks_permission(
    test_session: AsyncSession,
    sample_user: User,
) -> None:
    """PermissionChecker.check returns False when user lacks the permission."""
    checker = PermissionChecker(test_session)
    result = await checker.check(sample_user.id, "nonexistent_permission")
    assert result is False


async def test_permission_checker_require_raises(
    test_session: AsyncSession,
    sample_user: User,
) -> None:
    """PermissionChecker.require raises 403 when user lacks the permission."""
    checker = PermissionChecker(test_session)
    with pytest.raises(PermissionDeniedError):
        await checker.require(sample_user.id, "nonexistent_permission")


async def test_permission_checker_require_passes(
    test_session: AsyncSession,
    sample_user: User,
) -> None:
    """PermissionChecker.require passes when user has the permission."""
    checker = PermissionChecker(test_session)
    await checker.require(sample_user.id, "list_users")  # Should not raise
