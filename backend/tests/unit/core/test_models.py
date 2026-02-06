"""Unit tests for WP1 SQLAlchemy models."""

from __future__ import annotations

import uuid_utils
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from yourai.core.enums import UserStatus
from yourai.core.models import Permission, Role, Tenant, User


async def test_tenant_creation(test_session: AsyncSession) -> None:
    """Test creating a tenant with default values."""
    tenant = Tenant(
        id=uuid_utils.uuid7(),
        name="Acme Corp",
        slug="acme-corp",
    )
    test_session.add(tenant)
    await test_session.flush()

    result = await test_session.execute(select(Tenant).where(Tenant.slug == "acme-corp"))
    loaded = result.scalar_one()
    assert loaded.name == "Acme Corp"
    assert loaded.is_active is True


async def test_user_creation_with_tenant(
    test_session: AsyncSession,
    sample_tenant: Tenant,
) -> None:
    """Test creating a user linked to a tenant."""
    user = User(
        id=uuid_utils.uuid7(),
        tenant_id=sample_tenant.id,
        email="alice@example.com",
        given_name="Alice",
        family_name="Smith",
        status=UserStatus.PENDING,
        notification_preferences={},
    )
    test_session.add(user)
    await test_session.flush()

    result = await test_session.execute(select(User).where(User.email == "alice@example.com"))
    loaded = result.scalar_one()
    assert str(loaded.tenant_id) == str(sample_tenant.id)
    assert loaded.status == UserStatus.PENDING


async def test_role_permission_relationship(
    test_session: AsyncSession,
    sample_role: Role,
    sample_permission: Permission,
) -> None:
    """Test that roles load their permissions via the join table."""
    result = await test_session.execute(select(Role).where(Role.id == sample_role.id))
    loaded = result.scalar_one()
    assert len(loaded.permissions) == 1
    assert loaded.permissions[0].name == "list_users"


async def test_user_role_relationship(
    test_session: AsyncSession,
    sample_user: User,
    sample_role: Role,
) -> None:
    """Test that users load their roles via the join table."""
    result = await test_session.execute(select(User).where(User.id == sample_user.id))
    loaded = result.scalar_one()
    assert len(loaded.roles) == 1
    assert loaded.roles[0].name == "Admin"


async def test_permission_model(test_session: AsyncSession) -> None:
    """Test creating a standalone permission."""
    perm = Permission(
        id=uuid_utils.uuid7(),
        name="create_user",
        description="Create and invite new users",
    )
    test_session.add(perm)
    await test_session.flush()

    result = await test_session.execute(select(Permission).where(Permission.name == "create_user"))
    loaded = result.scalar_one()
    assert loaded.description == "Create and invite new users"
