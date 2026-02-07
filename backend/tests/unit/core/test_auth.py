"""Unit tests for AuthService — token creation and verification."""

from __future__ import annotations

import time

import pytest
import uuid_utils
from jose import jwt

from yourai.core.auth import AuthService
from yourai.core.config import settings
from yourai.core.exceptions import UnauthorisedError


@pytest.fixture
def auth_service() -> AuthService:
    return AuthService()


async def test_create_access_token(auth_service: AuthService) -> None:
    """Creating an access token returns a valid JWT string."""
    user_id = uuid_utils.uuid7()
    tenant_id = uuid_utils.uuid7()
    token = await auth_service.create_access_token(user_id, tenant_id, "test@example.com")
    assert isinstance(token, str)
    assert len(token) > 0


async def test_verify_token_roundtrip(auth_service: AuthService) -> None:
    """A token created by create_access_token can be verified."""
    user_id = uuid_utils.uuid7()
    tenant_id = uuid_utils.uuid7()
    token = await auth_service.create_access_token(user_id, tenant_id, "test@example.com")

    claims = await auth_service.verify_token(token)
    assert claims.sub == str(user_id)
    assert str(claims.tenant_id) == str(tenant_id)
    assert claims.email == "test@example.com"


async def test_verify_token_expired_raises(auth_service: AuthService) -> None:
    """An expired token raises UnauthorisedError."""
    user_id = uuid_utils.uuid7()
    tenant_id = uuid_utils.uuid7()

    # Create a token that expired 1 hour ago
    payload = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "email": "test@example.com",
        "exp": int(time.time()) - 3600,
        "iat": int(time.time()) - 7200,
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

    with pytest.raises(UnauthorisedError):
        await auth_service.verify_token(token)


async def test_verify_token_invalid_signature_raises(auth_service: AuthService) -> None:
    """A token signed with a different key raises UnauthorisedError."""
    user_id = uuid_utils.uuid7()
    tenant_id = uuid_utils.uuid7()

    payload = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "email": "test@example.com",
        "exp": int(time.time()) + 3600,
        "iat": int(time.time()),
    }
    token = jwt.encode(payload, "wrong-secret", algorithm="HS256")

    with pytest.raises(UnauthorisedError):
        await auth_service.verify_token(token)


async def test_verify_token_missing_claims_raises(auth_service: AuthService) -> None:
    """A token missing required claims raises UnauthorisedError."""
    payload = {
        "sub": str(uuid_utils.uuid7()),
        # Missing: tenant_id, email
        "exp": int(time.time()) + 3600,
        "iat": int(time.time()),
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

    with pytest.raises(UnauthorisedError, match="missing required claims"):
        await auth_service.verify_token(token)


async def test_create_token_pair(auth_service: AuthService) -> None:
    """create_token_pair returns both access and refresh tokens."""
    user_id = uuid_utils.uuid7()
    tenant_id = uuid_utils.uuid7()
    pair = await auth_service.create_token_pair(user_id, tenant_id, "test@example.com")

    assert pair.access_token
    assert pair.refresh_token
    assert pair.expires_in > 0


async def test_refresh_token(auth_service: AuthService) -> None:
    """Refreshing a token returns a new valid token pair."""
    user_id = uuid_utils.uuid7()
    tenant_id = uuid_utils.uuid7()
    pair = await auth_service.create_token_pair(user_id, tenant_id, "test@example.com")

    new_pair = await auth_service.refresh_token(pair.refresh_token)
    assert new_pair.access_token
    # Verify the new access token is valid
    claims = await auth_service.verify_token(new_pair.access_token)
    assert claims.sub == str(user_id)
