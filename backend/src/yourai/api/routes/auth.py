"""Auth routes — token management and dev token issuance."""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from yourai.core.auth import AuthService
from yourai.core.config import settings
from yourai.core.database import get_db_session, set_tenant_context
from yourai.core.enums import UserStatus
from yourai.core.exceptions import UnauthorisedError
from yourai.core.middleware import get_current_user
from yourai.core.models import Role, User
from yourai.core.schemas import DevTokenRequest, TokenPair, UserResponse

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

_auth_service = AuthService()


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int
    user: UserResponse


@router.post("/login", response_model=LoginResponse)
async def login(
    body: LoginRequest,
    session: AsyncSession = Depends(get_db_session),
) -> LoginResponse:
    """Authenticate with email and password.

    Dev mode: accepts any password and looks up the user by email.
    Production: should be replaced with proper IdP integration.
    """
    # Look up user by email (across all tenants for dev simplicity)
    result = await session.execute(
        select(User)
        .options(selectinload(User.roles).selectinload(Role.permissions))
        .where(User.email == body.email)
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise UnauthorisedError("Invalid email or password.")

    if str(user.status) != UserStatus.ACTIVE.value:
        raise UnauthorisedError("User account is not active.")

    # Set tenant context for RLS
    await set_tenant_context(session, user.tenant_id)

    # Generate token pair
    token_pair = await _auth_service.create_token_pair(
        user_id=user.id,
        tenant_id=user.tenant_id,
        email=user.email,
    )

    user_response = UserResponse.model_validate(user)

    logger.info(
        "user_login",
        user_id=str(user.id),
        tenant_id=str(user.tenant_id),
        email=user.email,
    )

    return LoginResponse(
        access_token=token_pair.access_token,
        refresh_token=token_pair.refresh_token,
        expires_in=token_pair.expires_in,
        user=user_response,
    )


@router.get("/callback")
async def oauth_callback() -> dict[str, str]:
    """OAuth2 PKCE callback — placeholder for IdP integration."""
    return {"message": "OAuth callback placeholder. Configure an IdP for production."}


@router.post("/refresh", response_model=TokenPair)
async def refresh_token(body: dict[str, str]) -> TokenPair:
    """Exchange a refresh token for a new token pair."""
    refresh_token_str = body.get("refresh_token")
    if not refresh_token_str:
        raise UnauthorisedError("refresh_token is required.")
    return await _auth_service.refresh_token(refresh_token_str)


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: UserResponse = Depends(get_current_user),
) -> UserResponse:
    """Get the current authenticated user."""
    return current_user


@router.post("/logout", status_code=204)
async def logout(
    _user: UserResponse = Depends(get_current_user),
) -> Response:
    """Invalidate the current session (placeholder — stateless JWT)."""
    return Response(status_code=204)


@router.post("/dev-token", response_model=TokenPair)
async def create_dev_token(
    body: DevTokenRequest,
    _session: AsyncSession = Depends(get_db_session),
) -> TokenPair:
    """Issue a JWT for development/testing. Only available in debug mode."""
    if not settings.debug:
        raise UnauthorisedError("Dev token endpoint is only available in debug mode.")
    return await _auth_service.create_token_pair(
        user_id=body.user_id,
        tenant_id=body.tenant_id,
        email=body.email,
    )
