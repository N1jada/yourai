"""Authentication service — JWT creation and verification.

Dev mode: HS256 with symmetric jwt_secret_key.
Production: RS256 with JWKS URL (future enhancement).
"""

from __future__ import annotations

import time
from uuid import UUID

import structlog
from jose import JWTError, jwt

from yourai.core.config import settings
from yourai.core.exceptions import UnauthorisedError
from yourai.core.schemas import TokenClaims, TokenPair

logger = structlog.get_logger()


class AuthService:
    def verify_token(self, token: str) -> TokenClaims:
        """Validate JWT signature, expiry, and required claims. Raises 401 on failure."""
        try:
            if settings.jwks_url:
                # Production: RS256 with JWKS
                payload = jwt.decode(
                    token,
                    settings.jwks_url,
                    algorithms=["RS256"],
                    audience=settings.jwt_audience,
                )
            else:
                # Development: HS256 with symmetric secret
                payload = jwt.decode(
                    token,
                    settings.jwt_secret_key,
                    algorithms=[settings.jwt_algorithm],
                    options={"verify_aud": False, "verify_iss": False},
                )
        except JWTError as exc:
            logger.warning("auth_token_invalid", error=str(exc))
            raise UnauthorisedError("Invalid or expired token.") from exc

        sub = payload.get("sub")
        email = payload.get("email")
        tenant_id_raw = payload.get("tenant_id")
        exp = payload.get("exp")

        if not all([sub, email, tenant_id_raw, exp]):
            raise UnauthorisedError("Token missing required claims.")

        return TokenClaims(
            sub=str(sub),
            email=str(email),
            tenant_id=UUID(str(tenant_id_raw)),
            exp=int(exp),
        )

    def create_access_token(
        self,
        user_id: UUID,
        tenant_id: UUID,
        email: str,
    ) -> str:
        """Create an HS256 JWT for development/testing. Not for production use."""
        now = int(time.time())
        payload = {
            "sub": str(user_id),
            "tenant_id": str(tenant_id),
            "email": email,
            "exp": now + settings.jwt_access_token_expire_minutes * 60,
            "iat": now,
        }
        result: str = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
        return result

    def create_token_pair(
        self,
        user_id: UUID,
        tenant_id: UUID,
        email: str,
    ) -> TokenPair:
        """Create access + refresh token pair for dev/testing."""
        access_token = self.create_access_token(user_id, tenant_id, email)
        # Refresh token is a longer-lived access token for now
        now = int(time.time())
        refresh_payload = {
            "sub": str(user_id),
            "tenant_id": str(tenant_id),
            "email": email,
            "exp": now + 7 * 24 * 3600,  # 7 days
            "iat": now,
            "type": "refresh",
        }
        refresh_token = jwt.encode(
            refresh_payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
        )
        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.jwt_access_token_expire_minutes * 60,
        )

    def refresh_token(self, refresh_token_str: str) -> TokenPair:
        """Exchange a refresh token for a new token pair. Raises 401 if invalid."""
        claims = self.verify_token(refresh_token_str)
        return self.create_token_pair(
            user_id=UUID(claims.sub),
            tenant_id=claims.tenant_id,
            email=claims.email,
        )
