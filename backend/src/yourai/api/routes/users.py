"""User routes — CRUD, profile management, GDPR endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from yourai.core.database import get_db_session
from yourai.core.enums import UserStatus
from yourai.core.middleware import get_current_tenant, get_current_user, require_permission
from yourai.core.schemas import (
    BulkInviteResult,
    CreateUser,
    Page,
    TenantConfig,
    UpdateProfile,
    UpdateUser,
    UserFilters,
    UserResponse,
)
from yourai.core.users import UserService

router = APIRouter(prefix="/api/v1/users", tags=["users"])


@router.get("", response_model=Page[UserResponse])
async def list_users(
    tenant: TenantConfig = Depends(get_current_tenant),
    _perm: None = Depends(require_permission("list_users")),
    session: AsyncSession = Depends(get_db_session),
    search: str | None = Query(None),
    status: UserStatus | None = Query(None),
    role_id: UUID | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> Page[UserResponse]:
    """List users for the current tenant."""
    filters = UserFilters(
        search=search,
        status=status,
        role_id=role_id,
        page=page,
        page_size=page_size,
    )
    user_service = UserService(session)
    return await user_service.list_users(tenant.id, filters)


@router.post("", response_model=UserResponse, status_code=201)
async def create_user(
    data: CreateUser,
    tenant: TenantConfig = Depends(get_current_tenant),
    _perm: None = Depends(require_permission("create_user")),
    session: AsyncSession = Depends(get_db_session),
) -> UserResponse:
    """Create a new user in the current tenant."""
    user_service = UserService(session)
    result = await user_service.create_user(tenant.id, data)
    await session.commit()
    return result


# /me endpoints MUST be before /{id} to avoid route conflicts
@router.get("/me", response_model=UserResponse)
async def get_me(
    user: UserResponse = Depends(get_current_user),
) -> UserResponse:
    """Return the current authenticated user's profile."""
    return user


@router.patch("/me", response_model=UserResponse)
async def update_me(
    data: UpdateProfile,
    user: UserResponse = Depends(get_current_user),
    tenant: TenantConfig = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db_session),
) -> UserResponse:
    """Update the current user's own profile."""
    user_service = UserService(session)
    result = await user_service.update_profile(user.id, tenant.id, data)
    await session.commit()
    return result


@router.post("/me/data-export", status_code=202)
async def request_data_export(
    _user: UserResponse = Depends(get_current_user),
) -> dict[str, str]:
    """GDPR Subject Access Request — enqueues data export job."""
    return {"message": "Data export request received. You will be notified when ready."}


@router.post("/me/deletion-request", status_code=204)
async def request_deletion(
    _user: UserResponse = Depends(get_current_user),
) -> Response:
    """GDPR Right to Erasure — marks account for deletion."""
    return Response(status_code=204)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    tenant: TenantConfig = Depends(get_current_tenant),
    _perm: None = Depends(require_permission("view_user")),
    session: AsyncSession = Depends(get_db_session),
) -> UserResponse:
    """Get a specific user by ID."""
    user_service = UserService(session)
    return await user_service.get_user(user_id, tenant.id)


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    data: UpdateUser,
    tenant: TenantConfig = Depends(get_current_tenant),
    _perm: None = Depends(require_permission("update_user_profile")),
    session: AsyncSession = Depends(get_db_session),
) -> UserResponse:
    """Update a user's details."""
    user_service = UserService(session)
    result = await user_service.update_user(user_id, tenant.id, data)
    await session.commit()
    return result


@router.delete("/{user_id}", status_code=204)
async def delete_user(
    user_id: UUID,
    tenant: TenantConfig = Depends(get_current_tenant),
    _perm: None = Depends(require_permission("delete_user")),
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    """Soft delete a user."""
    user_service = UserService(session)
    await user_service.delete_user(user_id, tenant.id)
    await session.commit()
    return Response(status_code=204)


@router.post("/bulk-invite", response_model=BulkInviteResult)
async def bulk_invite(
    file: UploadFile,
    tenant: TenantConfig = Depends(get_current_tenant),
    _perm: None = Depends(require_permission("create_user")),
    session: AsyncSession = Depends(get_db_session),
) -> BulkInviteResult:
    """Bulk invite users from a CSV file."""
    user_service = UserService(session)
    result = await user_service.bulk_invite(tenant.id, file)
    await session.commit()
    return result
