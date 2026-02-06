"""Unit tests for UserService — status transitions, CRUD."""

from __future__ import annotations

import pytest
import uuid_utils
from sqlalchemy.ext.asyncio import AsyncSession

from yourai.core.enums import UserStatus
from yourai.core.exceptions import ConflictError, NotFoundError, ValidationError
from yourai.core.models import Tenant
from yourai.core.schemas import CreateUser, UpdateUser
from yourai.core.users import UserService


async def test_create_user(
    test_session: AsyncSession,
    sample_tenant: Tenant,
) -> None:
    """Creating a user returns a UserResponse with PENDING status."""
    svc = UserService(test_session)
    data = CreateUser(
        email="alice@example.com",
        given_name="Alice",
        family_name="Smith",
    )
    user = await svc.create_user(sample_tenant.id, data)
    assert user.email == "alice@example.com"
    assert user.status == UserStatus.PENDING
    assert str(user.tenant_id) == str(sample_tenant.id)


async def test_create_user_duplicate_email_raises_conflict(
    test_session: AsyncSession,
    sample_tenant: Tenant,
) -> None:
    """Creating a user with a duplicate email raises ConflictError."""
    svc = UserService(test_session)
    data = CreateUser(
        email="dup@example.com",
        given_name="First",
        family_name="User",
    )
    await svc.create_user(sample_tenant.id, data)

    with pytest.raises(ConflictError):
        await svc.create_user(sample_tenant.id, data)


async def test_get_user_not_found_raises(
    test_session: AsyncSession,
    sample_tenant: Tenant,
) -> None:
    """Getting a non-existent user raises NotFoundError."""
    svc = UserService(test_session)
    with pytest.raises(NotFoundError):
        await svc.get_user(uuid_utils.uuid7(), sample_tenant.id)


async def test_valid_transition_pending_to_active(
    test_session: AsyncSession,
    sample_tenant: Tenant,
) -> None:
    """PENDING -> ACTIVE is a valid transition."""
    svc = UserService(test_session)
    data = CreateUser(email="t1@example.com", given_name="T", family_name="One")
    user = await svc.create_user(sample_tenant.id, data)

    updated = await svc.update_user(user.id, sample_tenant.id, UpdateUser(status=UserStatus.ACTIVE))
    assert updated.status == UserStatus.ACTIVE


async def test_valid_transition_active_to_disabled(
    test_session: AsyncSession,
    sample_tenant: Tenant,
) -> None:
    """ACTIVE -> DISABLED is a valid transition."""
    svc = UserService(test_session)
    data = CreateUser(email="t2@example.com", given_name="T", family_name="Two")
    user = await svc.create_user(sample_tenant.id, data)

    # First activate
    await svc.update_user(user.id, sample_tenant.id, UpdateUser(status=UserStatus.ACTIVE))
    # Then disable
    updated = await svc.update_user(
        user.id, sample_tenant.id, UpdateUser(status=UserStatus.DISABLED)
    )
    assert updated.status == UserStatus.DISABLED


async def test_valid_transition_active_to_deleted(
    test_session: AsyncSession,
    sample_tenant: Tenant,
) -> None:
    """ACTIVE -> DELETED is a valid transition and sets deleted_at."""
    svc = UserService(test_session)
    data = CreateUser(email="t3@example.com", given_name="T", family_name="Three")
    user = await svc.create_user(sample_tenant.id, data)
    await svc.update_user(user.id, sample_tenant.id, UpdateUser(status=UserStatus.ACTIVE))

    updated = await svc.update_user(
        user.id, sample_tenant.id, UpdateUser(status=UserStatus.DELETED)
    )
    assert updated.status == UserStatus.DELETED


async def test_valid_transition_disabled_to_active(
    test_session: AsyncSession,
    sample_tenant: Tenant,
) -> None:
    """DISABLED -> ACTIVE is a valid transition."""
    svc = UserService(test_session)
    data = CreateUser(email="t4@example.com", given_name="T", family_name="Four")
    user = await svc.create_user(sample_tenant.id, data)
    await svc.update_user(user.id, sample_tenant.id, UpdateUser(status=UserStatus.ACTIVE))
    await svc.update_user(user.id, sample_tenant.id, UpdateUser(status=UserStatus.DISABLED))

    updated = await svc.update_user(user.id, sample_tenant.id, UpdateUser(status=UserStatus.ACTIVE))
    assert updated.status == UserStatus.ACTIVE


async def test_invalid_transition_pending_to_disabled_raises(
    test_session: AsyncSession,
    sample_tenant: Tenant,
) -> None:
    """PENDING -> DISABLED is not a valid transition."""
    svc = UserService(test_session)
    data = CreateUser(email="t5@example.com", given_name="T", family_name="Five")
    user = await svc.create_user(sample_tenant.id, data)

    with pytest.raises(ValidationError, match="Cannot transition"):
        await svc.update_user(user.id, sample_tenant.id, UpdateUser(status=UserStatus.DISABLED))


async def test_invalid_transition_deleted_to_active_raises(
    test_session: AsyncSession,
    sample_tenant: Tenant,
) -> None:
    """DELETED -> ACTIVE is not a valid transition."""
    svc = UserService(test_session)
    data = CreateUser(email="t6@example.com", given_name="T", family_name="Six")
    user = await svc.create_user(sample_tenant.id, data)
    await svc.update_user(user.id, sample_tenant.id, UpdateUser(status=UserStatus.ACTIVE))
    await svc.update_user(user.id, sample_tenant.id, UpdateUser(status=UserStatus.DELETED))

    with pytest.raises(ValidationError, match="Cannot transition"):
        await svc.update_user(user.id, sample_tenant.id, UpdateUser(status=UserStatus.ACTIVE))


async def test_invalid_transition_pending_to_deleted_raises(
    test_session: AsyncSession,
    sample_tenant: Tenant,
) -> None:
    """PENDING -> DELETED is not a valid transition."""
    svc = UserService(test_session)
    data = CreateUser(email="t7@example.com", given_name="T", family_name="Seven")
    user = await svc.create_user(sample_tenant.id, data)

    with pytest.raises(ValidationError, match="Cannot transition"):
        await svc.update_user(user.id, sample_tenant.id, UpdateUser(status=UserStatus.DELETED))


async def test_soft_delete_user(
    test_session: AsyncSession,
    sample_tenant: Tenant,
) -> None:
    """Soft deleting a user sets status=DELETED."""
    svc = UserService(test_session)
    data = CreateUser(email="del@example.com", given_name="Del", family_name="User")
    user = await svc.create_user(sample_tenant.id, data)
    await svc.update_user(user.id, sample_tenant.id, UpdateUser(status=UserStatus.ACTIVE))

    await svc.delete_user(user.id, sample_tenant.id)

    loaded = await svc.get_user(user.id, sample_tenant.id)
    assert loaded.status == UserStatus.DELETED


async def test_list_users_pagination(
    test_session: AsyncSession,
    sample_tenant: Tenant,
) -> None:
    """Listing users returns paginated results."""
    svc = UserService(test_session)

    for i in range(5):
        await svc.create_user(
            sample_tenant.id,
            CreateUser(
                email=f"user{i}@example.com",
                given_name=f"User{i}",
                family_name="Test",
            ),
        )

    from yourai.core.schemas import UserFilters

    page = await svc.list_users(sample_tenant.id, UserFilters(page=1, page_size=3))
    assert len(page.items) == 3
    assert page.total == 5
    assert page.has_next is True
