"""Auth routes — token management and dev token issuance."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from yourai.core.auth import AuthService
from yourai.core.config import settings
from yourai.core.database import get_db_session
from yourai.core.exceptions import UnauthorisedError
from yourai.core.middleware import get_current_user
from yourai.core.schemas import DevTokenRequest, TokenPair, UserResponse

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

_auth_service = AuthService()


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
