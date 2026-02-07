"""FastAPI dependency functions for authentication, tenant isolation, and RBAC.

These dependencies are injected into route handlers via ``Depends()``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

import structlog
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from yourai.core.auth import AuthService
from yourai.core.database import get_db_session, set_tenant_context
from yourai.core.enums import UserStatus
from yourai.core.exceptions import UnauthorisedError, UserNotActiveError
from yourai.core.roles import PermissionChecker
from yourai.core.tenant import TenantService
from yourai.core.users import UserService

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine

    from sqlalchemy.ext.asyncio import AsyncSession

    from yourai.core.schemas import TenantConfig, TokenClaims, UserResponse

logger = structlog.get_logger()

_bearer_scheme = HTTPBearer(auto_error=False)
_auth_service = AuthService()


async def get_token_claims(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> TokenClaims:
    """Extract and verify JWT from the Authorization header."""
    if credentials is None:
        raise UnauthorisedError("Authentication required.")
    return await _auth_service.verify_token(credentials.credentials)


async def get_current_tenant(
    request: Request,
    claims: TokenClaims = Depends(get_token_claims),
    session: AsyncSession = Depends(get_db_session),
) -> TenantConfig:
    """Load tenant from JWT claims and set RLS context.

    Side effect: executes SET LOCAL app.current_tenant_id.
    """
    await set_tenant_context(session, claims.tenant_id)

    tenant_service = TenantService(session)
    tenant = await tenant_service.get_tenant(claims.tenant_id)

    request.state.tenant_id = claims.tenant_id
    request.state.tenant = tenant
    return tenant


async def get_current_user(
    request: Request,
    claims: TokenClaims = Depends(get_token_claims),
    tenant: TenantConfig = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db_session),
) -> UserResponse:
    """Verify JWT, load user record, check user is active.

    Raises 401 (invalid token), 423 (user not active).
    """
    user_service = UserService(session)
    user = await user_service.get_user(UUID(claims.sub), tenant.id)

    if user.status != UserStatus.ACTIVE:
        raise UserNotActiveError(
            f"User account is {user.status}. Please contact your administrator."
        )

    request.state.user_id = user.id
    request.state.user = user
    return user


def require_permission(
    permission: str,
) -> Callable[..., Coroutine[Any, Any, None]]:
    """Return a FastAPI dependency that raises 403 if the user lacks the permission."""

    async def _check(
        user: UserResponse = Depends(get_current_user),
        session: AsyncSession = Depends(get_db_session),
    ) -> None:
        checker = PermissionChecker(session)
        await checker.require(user.id, permission, user.tenant_id)

    return _check
