"""Role and permission routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from yourai.core.database import get_db_session
from yourai.core.middleware import get_current_tenant, require_permission
from yourai.core.roles import RoleService
from yourai.core.schemas import (
    AssignRoles,
    CreateRole,
    PermissionResponse,
    RoleResponse,
    TenantConfig,
    UpdateRole,
    UserResponse,
)

router = APIRouter(tags=["roles"])


@router.get("/api/v1/roles", response_model=list[RoleResponse])
async def list_roles(
    tenant: TenantConfig = Depends(get_current_tenant),
    _perm: None = Depends(require_permission("list_user_roles")),
    session: AsyncSession = Depends(get_db_session),
) -> list[RoleResponse]:
    """List all roles for the current tenant."""
    role_service = RoleService(session)
    return await role_service.list_roles(tenant.id)


@router.post("/api/v1/roles", response_model=RoleResponse, status_code=201)
async def create_role(
    data: CreateRole,
    tenant: TenantConfig = Depends(get_current_tenant),
    _perm: None = Depends(require_permission("list_user_roles")),
    session: AsyncSession = Depends(get_db_session),
) -> RoleResponse:
    """Create a new role."""
    role_service = RoleService(session)
    result = await role_service.create_role(tenant.id, data)
    await session.commit()
    return result


@router.get("/api/v1/roles/{role_id}", response_model=RoleResponse)
async def get_role(
    role_id: UUID,
    tenant: TenantConfig = Depends(get_current_tenant),
    _perm: None = Depends(require_permission("list_user_roles")),
    session: AsyncSession = Depends(get_db_session),
) -> RoleResponse:
    """Get a specific role by ID."""
    role_service = RoleService(session)
    return await role_service.get_role(role_id, tenant.id)


@router.patch("/api/v1/roles/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: UUID,
    data: UpdateRole,
    tenant: TenantConfig = Depends(get_current_tenant),
    _perm: None = Depends(require_permission("list_user_roles")),
    session: AsyncSession = Depends(get_db_session),
) -> RoleResponse:
    """Update a role."""
    role_service = RoleService(session)
    result = await role_service.update_role(role_id, tenant.id, data)
    await session.commit()
    return result


@router.delete("/api/v1/roles/{role_id}", status_code=204)
async def delete_role(
    role_id: UUID,
    tenant: TenantConfig = Depends(get_current_tenant),
    _perm: None = Depends(require_permission("delete_user_roles")),
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    """Delete a role."""
    role_service = RoleService(session)
    await role_service.delete_role(role_id, tenant.id)
    await session.commit()
    return Response(status_code=204)


@router.put("/api/v1/users/{user_id}/roles", response_model=UserResponse)
async def assign_user_roles(
    user_id: UUID,
    data: AssignRoles,
    tenant: TenantConfig = Depends(get_current_tenant),
    _perm: None = Depends(require_permission("update_user_role")),
    session: AsyncSession = Depends(get_db_session),
) -> UserResponse:
    """Replace all roles for a user."""
    role_service = RoleService(session)
    result = await role_service.assign_roles_to_user(user_id, tenant.id, data.role_ids)
    await session.commit()
    return result


@router.get("/api/v1/permissions", response_model=list[PermissionResponse])
async def list_permissions(
    _tenant: TenantConfig = Depends(get_current_tenant),
    _perm: None = Depends(require_permission("list_user_roles")),
    session: AsyncSession = Depends(get_db_session),
) -> list[PermissionResponse]:
    """List all available permissions."""
    role_service = RoleService(session)
    return await role_service.list_permissions()
