"""User service — CRUD for users table.

Every query filters by tenant_id at the application level (belt-and-braces with RLS).
"""

from __future__ import annotations

import csv
import io
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import structlog
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

if TYPE_CHECKING:
    from uuid import UUID

    from fastapi import UploadFile
    from sqlalchemy.ext.asyncio import AsyncSession

from yourai.core.enums import UserStatus
from yourai.core.exceptions import ConflictError, NotFoundError, ValidationError
from yourai.core.models import Role, User, UserRole
from yourai.core.schemas import (
    BulkInviteResult,
    CreateUser,
    Page,
    UpdateProfile,
    UpdateUser,
    UserFilters,
    UserResponse,
)

logger = structlog.get_logger()

# Valid status transitions: from -> set of allowed targets
_VALID_TRANSITIONS: dict[UserStatus, set[UserStatus]] = {
    UserStatus.PENDING: {UserStatus.ACTIVE},
    UserStatus.ACTIVE: {UserStatus.DISABLED, UserStatus.DELETED},
    UserStatus.DISABLED: {UserStatus.ACTIVE},
    UserStatus.DELETED: set(),
}


def _validate_status_transition(current: UserStatus, target: UserStatus) -> None:
    allowed = _VALID_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise ValidationError(
            f"Cannot transition from '{current}' to '{target}'.",
            detail={"current_status": current, "target_status": target},
        )


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_user(self, user_id: UUID, tenant_id: UUID) -> UserResponse:
        """Fetch a single user by ID within tenant. Raises 404 if not found."""
        result = await self._session.execute(
            select(User)
            .options(selectinload(User.roles).selectinload(Role.permissions))
            .where(User.id == user_id, User.tenant_id == tenant_id)
        )
        user = result.scalar_one_or_none()
        if user is None:
            raise NotFoundError("User not found.")
        return UserResponse.model_validate(user)

    async def list_users(self, tenant_id: UUID, filters: UserFilters) -> Page[UserResponse]:
        """List users for a tenant with optional filtering and pagination."""
        query = (
            select(User)
            .options(selectinload(User.roles).selectinload(Role.permissions))
            .where(User.tenant_id == tenant_id)
        )

        if filters.status is not None:
            query = query.where(User.status == filters.status)

        if filters.search is not None:
            search_term = f"%{filters.search}%"
            query = query.where(
                or_(
                    User.email.ilike(search_term),
                    User.given_name.ilike(search_term),
                    User.family_name.ilike(search_term),
                )
            )

        if filters.role_id is not None:
            query = query.join(User.roles).where(Role.id == filters.role_id)

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self._session.execute(count_query)
        total = total_result.scalar_one()

        # Paginate
        offset = (filters.page - 1) * filters.page_size
        query = query.order_by(User.created_at.desc()).offset(offset).limit(filters.page_size)

        result = await self._session.execute(query)
        users = list(result.scalars().unique())

        return Page(
            items=[UserResponse.model_validate(u) for u in users],
            total=total,
            page=filters.page,
            page_size=filters.page_size,
            has_next=(offset + filters.page_size) < total,
        )

    async def create_user(self, tenant_id: UUID, data: CreateUser) -> UserResponse:
        """Create a new user within a tenant. Raises 409 if email already exists."""
        # Check for existing email in tenant
        existing = await self._session.execute(
            select(User).where(
                User.tenant_id == tenant_id,
                User.email == data.email,
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise ConflictError("A user with this email already exists in this tenant.")

        user = User(
            tenant_id=tenant_id,
            email=data.email,
            given_name=data.given_name,
            family_name=data.family_name,
            job_role=data.job_role,
            status=UserStatus.PENDING,
        )
        self._session.add(user)
        await self._session.flush()

        # Assign roles if provided
        if data.role_ids:
            for role_id in data.role_ids:
                role_result = await self._session.execute(
                    select(Role).where(Role.id == role_id, Role.tenant_id == tenant_id)
                )
                if role_result.scalar_one_or_none() is None:
                    raise NotFoundError(f"Role {role_id} not found.")
                self._session.add(UserRole(user_id=user.id, role_id=role_id))
            await self._session.flush()

        await self._session.refresh(user)
        logger.info(
            "user_created",
            user_id=str(user.id),
            tenant_id=str(tenant_id),
            email=data.email,
        )
        return await self.get_user(user.id, tenant_id)

    async def update_user(self, user_id: UUID, tenant_id: UUID, data: UpdateUser) -> UserResponse:
        """Update a user. Validates status transitions."""
        result = await self._session.execute(
            select(User).where(User.id == user_id, User.tenant_id == tenant_id)
        )
        user = result.scalar_one_or_none()
        if user is None:
            raise NotFoundError("User not found.")

        update_data = data.model_dump(exclude_unset=True)

        # Validate status transition if status is being changed
        if "status" in update_data and update_data["status"] is not None:
            new_status = UserStatus(update_data["status"])
            _validate_status_transition(UserStatus(user.status), new_status)

            if new_status == UserStatus.DELETED:
                update_data["deleted_at"] = datetime.now(UTC)

        for field, value in update_data.items():
            setattr(user, field, value)

        await self._session.flush()
        logger.info(
            "user_updated",
            user_id=str(user_id),
            tenant_id=str(tenant_id),
        )
        return await self.get_user(user_id, tenant_id)

    async def update_profile(
        self, user_id: UUID, tenant_id: UUID, data: UpdateProfile
    ) -> UserResponse:
        """Update own profile fields."""
        result = await self._session.execute(
            select(User).where(User.id == user_id, User.tenant_id == tenant_id)
        )
        user = result.scalar_one_or_none()
        if user is None:
            raise NotFoundError("User not found.")

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(user, field, value)

        await self._session.flush()
        return await self.get_user(user_id, tenant_id)

    async def delete_user(self, user_id: UUID, tenant_id: UUID) -> None:
        """Soft delete: sets status=deleted, deleted_at=now."""
        result = await self._session.execute(
            select(User).where(User.id == user_id, User.tenant_id == tenant_id)
        )
        user = result.scalar_one_or_none()
        if user is None:
            raise NotFoundError("User not found.")

        _validate_status_transition(UserStatus(user.status), UserStatus.DELETED)
        user.status = UserStatus.DELETED
        user.deleted_at = datetime.now(UTC)
        await self._session.flush()
        logger.info(
            "user_deleted",
            user_id=str(user_id),
            tenant_id=str(tenant_id),
        )

    async def bulk_invite(self, tenant_id: UUID, csv_file: UploadFile) -> BulkInviteResult:
        """Invite users from CSV. Columns: email, given_name, family_name, role."""
        content = await csv_file.read()
        text = content.decode("utf-8")
        reader = csv.DictReader(io.StringIO(text))

        created = 0
        skipped = 0
        errors: list[dict[str, object]] = []

        for row_num, row in enumerate(reader, start=2):
            email = row.get("email", "").strip()
            given_name = row.get("given_name", "").strip()
            family_name = row.get("family_name", "").strip()

            if not email or not given_name or not family_name:
                errors.append({"row": row_num, "error": "Missing required fields."})
                continue

            # Check if user already exists
            existing = await self._session.execute(
                select(User).where(
                    User.tenant_id == tenant_id,
                    User.email == email,
                )
            )
            if existing.scalar_one_or_none() is not None:
                skipped += 1
                continue

            try:
                user = User(
                    tenant_id=tenant_id,
                    email=email,
                    given_name=given_name,
                    family_name=family_name,
                    status=UserStatus.PENDING,
                )
                self._session.add(user)
                await self._session.flush()
                created += 1
            except Exception as exc:
                errors.append({"row": row_num, "error": str(exc)})

        logger.info(
            "bulk_invite_complete",
            tenant_id=str(tenant_id),
            created=created,
            skipped=skipped,
            errors=len(errors),
        )
        return BulkInviteResult(created=created, skipped=skipped, errors=errors)
