"""Profile routes — thin aliases for /users/me endpoints.

The frontend calls GET/PATCH /api/v1/profile. These delegate to the
same service methods used by the /users/me routes.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from yourai.core.database import get_db_session
from yourai.core.middleware import get_current_tenant, get_current_user
from yourai.core.schemas import TenantConfig, UpdateProfile, UserResponse
from yourai.core.users import UserService

router = APIRouter(prefix="/api/v1/profile", tags=["profile"])


@router.get("", response_model=UserResponse)
async def get_profile(
    user: UserResponse = Depends(get_current_user),
) -> UserResponse:
    """Return the current authenticated user's profile."""
    return user


@router.patch("", response_model=UserResponse)
async def update_profile(
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
