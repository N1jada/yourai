"""Role service and permission checker.

Every query filters by tenant_id at the application level.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog
from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

from yourai.core.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from yourai.core.models import Permission, Role, RolePermission, User, UserRole
from yourai.core.schemas import (
    CreateRole,
    PermissionResponse,
    RoleResponse,
    UpdateRole,
    UserResponse,
)

logger = structlog.get_logger()


class RoleService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_roles(self, tenant_id: UUID) -> list[RoleResponse]:
        """List all roles for a tenant."""
        result = await self._session.execute(
            select(Role)
            .options(selectinload(Role.permissions))
            .where(Role.tenant_id == tenant_id)
            .order_by(Role.name)
        )
        roles = list(result.scalars().unique())
        return [RoleResponse.model_validate(r) for r in roles]

    async def get_role(self, role_id: UUID, tenant_id: UUID) -> RoleResponse:
        """Fetch a single role. Raises 404 if not found."""
        result = await self._session.execute(
            select(Role)
            .options(selectinload(Role.permissions))
            .where(Role.id == role_id, Role.tenant_id == tenant_id)
        )
        role = result.scalar_one_or_none()
        if role is None:
            raise NotFoundError("Role not found.")
        return RoleResponse.model_validate(role)

    async def create_role(self, tenant_id: UUID, data: CreateRole) -> RoleResponse:
        """Create a new role. Raises 409 if name already exists in tenant."""
        # Check for existing name in tenant
        existing = await self._session.execute(
            select(Role).where(Role.tenant_id == tenant_id, Role.name == data.name)
        )
        if existing.scalar_one_or_none() is not None:
            raise ConflictError("A role with this name already exists in this tenant.")

        role = Role(
            tenant_id=tenant_id,
            name=data.name,
            description=data.description,
        )
        self._session.add(role)
        await self._session.flush()

        # Assign permissions if provided
        if data.permission_ids:
            for perm_id in data.permission_ids:
                perm_result = await self._session.execute(
                    select(Permission).where(Permission.id == perm_id)
                )
                if perm_result.scalar_one_or_none() is None:
                    raise NotFoundError(f"Permission {perm_id} not found.")
                self._session.add(RolePermission(role_id=role.id, permission_id=perm_id))
            await self._session.flush()

        logger.info(
            "role_created",
            role_id=str(role.id),
            tenant_id=str(tenant_id),
            name=data.name,
        )
        return await self.get_role(role.id, tenant_id)

    async def update_role(self, role_id: UUID, tenant_id: UUID, data: UpdateRole) -> RoleResponse:
        """Update a role's name, description, or permissions."""
        result = await self._session.execute(
            select(Role).where(Role.id == role_id, Role.tenant_id == tenant_id)
        )
        role = result.scalar_one_or_none()
        if role is None:
            raise NotFoundError("Role not found.")

        if data.name is not None:
            # Check uniqueness
            existing = await self._session.execute(
                select(Role).where(
                    Role.tenant_id == tenant_id,
                    Role.name == data.name,
                    Role.id != role_id,
                )
            )
            if existing.scalar_one_or_none() is not None:
                raise ConflictError("A role with this name already exists in this tenant.")
            role.name = data.name

        if data.description is not None:
            role.description = data.description

        if data.permission_ids is not None:
            # Replace all permissions
            await self._session.execute(
                delete(RolePermission).where(RolePermission.role_id == role_id)
            )
            for perm_id in data.permission_ids:
                perm_result = await self._session.execute(
                    select(Permission).where(Permission.id == perm_id)
                )
                if perm_result.scalar_one_or_none() is None:
                    raise NotFoundError(f"Permission {perm_id} not found.")
                self._session.add(RolePermission(role_id=role_id, permission_id=perm_id))

        await self._session.flush()
        logger.info(
            "role_updated",
            role_id=str(role_id),
            tenant_id=str(tenant_id),
        )
        return await self.get_role(role_id, tenant_id)

    async def delete_role(self, role_id: UUID, tenant_id: UUID) -> None:
        """Delete a role and all its permission/user associations."""
        result = await self._session.execute(
            select(Role).where(Role.id == role_id, Role.tenant_id == tenant_id)
        )
        role = result.scalar_one_or_none()
        if role is None:
            raise NotFoundError("Role not found.")

        await self._session.delete(role)
        await self._session.flush()
        logger.info(
            "role_deleted",
            role_id=str(role_id),
            tenant_id=str(tenant_id),
        )

    async def assign_roles_to_user(
        self, user_id: UUID, tenant_id: UUID, role_ids: list[UUID]
    ) -> UserResponse:
        """Replace all roles for a user."""
        # Verify user exists
        user_result = await self._session.execute(
            select(User).where(User.id == user_id, User.tenant_id == tenant_id)
        )
        if user_result.scalar_one_or_none() is None:
            raise NotFoundError("User not found.")

        # Remove existing roles
        await self._session.execute(delete(UserRole).where(UserRole.user_id == user_id))

        # Assign new roles
        for role_id in role_ids:
            role_result = await self._session.execute(
                select(Role).where(Role.id == role_id, Role.tenant_id == tenant_id)
            )
            if role_result.scalar_one_or_none() is None:
                raise NotFoundError(f"Role {role_id} not found.")
            self._session.add(UserRole(user_id=user_id, role_id=role_id))

        await self._session.flush()
        logger.info(
            "user_roles_assigned",
            user_id=str(user_id),
            tenant_id=str(tenant_id),
            role_ids=[str(r) for r in role_ids],
        )

        # Return updated user
        from yourai.core.users import UserService

        user_service = UserService(self._session)
        return await user_service.get_user(user_id, tenant_id)

    async def list_permissions(self) -> list[PermissionResponse]:
        """List all platform permissions."""
        result = await self._session.execute(select(Permission).order_by(Permission.name))
        permissions = list(result.scalars())
        return [PermissionResponse.model_validate(p) for p in permissions]


class PermissionChecker:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def check(self, user_id: UUID, permission: str) -> bool:
        """Return True if user has the permission via any assigned role."""
        result = await self._session.execute(
            select(Permission.name)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .join(Role, Role.id == RolePermission.role_id)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user_id, Permission.name == permission)
        )
        return result.scalar_one_or_none() is not None

    async def require(self, user_id: UUID, permission: str) -> None:
        """Raise 403 if user lacks the permission."""
        has_permission = await self.check(user_id, permission)
        if not has_permission:
            raise PermissionDeniedError(f"Permission '{permission}' is required for this action.")
