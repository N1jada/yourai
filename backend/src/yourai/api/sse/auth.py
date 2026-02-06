"""JWT authentication for SSE endpoints.

SSE connections cannot send custom headers via the browser EventSource API,
so we support JWT via:
1. Authorization header (for non-browser clients / custom EventSource wrappers)
2. ``token`` query parameter (for browser EventSource)
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

import structlog
from fastapi import HTTPException, Request, status
from jose import JWTError, jwt

from yourai.core.config import settings

logger = structlog.get_logger()


@dataclass(frozen=True, slots=True)
class SSETokenClaims:
    """Minimal claims extracted from the JWT for SSE scoping."""

    sub: str
    user_id: UUID
    tenant_id: UUID


async def verify_sse_token(request: Request) -> SSETokenClaims:
    """Extract and verify JWT from the request.

    Checks (in order):
    1. ``Authorization: Bearer <token>`` header
    2. ``?token=<token>`` query parameter

    Raises HTTP 401 if no valid token is found.
    """
    token: str | None = None

    # Try Authorization header first
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        token = auth_header[7:]

    # Fall back to query parameter
    if token is None:
        token = request.query_params.get("token")

    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "unauthorised", "message": "Authentication required."},
        )

    try:
        # When JWKS is configured, the full auth middleware handles key rotation.
        # For SSE, we do a lightweight decode with the same configuration.
        # In production, this would use the JWKS keyset; here we accept HS256
        # for development when jwks_url is not configured.
        decode_options: dict[str, bool] = {}
        algorithms = ["RS256"]
        key: str = settings.jwks_url

        if not settings.jwks_url:
            # Development mode — accept HS256 with a symmetric secret
            algorithms = ["HS256"]
            key = settings.jwt_issuer or "dev-secret"
            decode_options = {"verify_aud": False, "verify_iss": False}

        payload = jwt.decode(
            token,
            key,
            algorithms=algorithms,
            audience=settings.jwt_audience
            if decode_options.get("verify_aud") is not False
            else None,
            options=decode_options,
        )

        sub = payload.get("sub")
        tenant_id_raw = payload.get("tenant_id")

        if sub is None or tenant_id_raw is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "unauthorised", "message": "Token missing required claims."},
            )

        return SSETokenClaims(
            sub=sub,
            user_id=UUID(sub),
            tenant_id=UUID(tenant_id_raw),
        )

    except JWTError as exc:
        logger.warning("sse_auth_failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "unauthorised", "message": "Invalid or expired token."},
        ) from exc
