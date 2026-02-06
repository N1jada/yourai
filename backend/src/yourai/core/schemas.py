"""Pydantic v2 request/response schemas for WP1 core endpoints.

All schemas match API_CONTRACTS.md §2.1 and §3.1–3.4.
"""

from __future__ import annotations

from datetime import datetime
from typing import Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr

from yourai.core.enums import SubscriptionTier, UserStatus

T = TypeVar("T")


# ---------------------------------------------------------------------------
# Shared
# ---------------------------------------------------------------------------


class Page(BaseModel, Generic[T]):
    """Offset-based pagination wrapper."""

    items: list[T]
    total: int
    page: int
    page_size: int
    has_next: bool


class ErrorResponse(BaseModel):
    """Standard error response body."""

    code: str
    message: str
    detail: dict[str, object] | None = None


# ---------------------------------------------------------------------------
# Tenant
# ---------------------------------------------------------------------------


class BrandingConfig(BaseModel):
    logo_url: str | None = None
    favicon_url: str | None = None
    app_name: str | None = None
    primary_colour: str | None = None
    secondary_colour: str | None = None
    custom_domain: str | None = None
    disclaimer_text: str | None = None


class AIConfig(BaseModel):
    confidence_thresholds: dict[str, object] | None = None
    topic_restrictions: list[str] | None = None
    model_overrides: dict[str, object] | None = None


class TenantConfig(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str
    industry_vertical: str | None
    branding: BrandingConfig
    ai_config: AIConfig
    subscription_tier: SubscriptionTier
    credit_limit: float
    billing_period_start: datetime | None
    billing_period_end: datetime | None
    is_active: bool
    news_feed_urls: list[str]
    external_source_integrations: list[dict[str, object]]
    vector_namespace: str | None


class UpdateTenant(BaseModel):
    name: str | None = None
    industry_vertical: str | None = None
    branding_config: dict[str, object] | None = None
    ai_config: dict[str, object] | None = None
    news_feed_urls: list[str] | None = None
    external_source_integrations: list[dict[str, object]] | None = None


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


class TokenClaims(BaseModel):
    sub: str
    email: str
    tenant_id: UUID
    exp: int


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int


class DevTokenRequest(BaseModel):
    user_id: UUID
    tenant_id: UUID
    email: str


# ---------------------------------------------------------------------------
# Permission
# ---------------------------------------------------------------------------


class PermissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None


# ---------------------------------------------------------------------------
# Role
# ---------------------------------------------------------------------------


class RoleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    name: str
    description: str | None
    permissions: list[PermissionResponse]
    created_at: datetime | None = None


class CreateRole(BaseModel):
    name: str
    description: str | None = None
    permission_ids: list[UUID] | None = None


class UpdateRole(BaseModel):
    name: str | None = None
    description: str | None = None
    permission_ids: list[UUID] | None = None


class AssignRoles(BaseModel):
    role_ids: list[UUID]


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    email: str
    given_name: str
    family_name: str
    job_role: str | None
    status: UserStatus
    last_active_at: datetime | None
    notification_preferences: dict[str, object]
    roles: list[RoleResponse]
    created_at: datetime | None = None
    updated_at: datetime | None = None


class CreateUser(BaseModel):
    email: EmailStr
    given_name: str
    family_name: str
    job_role: str | None = None
    role_ids: list[UUID] | None = None


class UpdateUser(BaseModel):
    given_name: str | None = None
    family_name: str | None = None
    job_role: str | None = None
    status: UserStatus | None = None
    notification_preferences: dict[str, object] | None = None


class UpdateProfile(BaseModel):
    """Fields a user can update on their own profile."""

    given_name: str | None = None
    family_name: str | None = None
    job_role: str | None = None
    notification_preferences: dict[str, object] | None = None


class UserFilters(BaseModel):
    search: str | None = None
    status: UserStatus | None = None
    role_id: UUID | None = None
    page: int = 1
    page_size: int = 20


class BulkInviteResult(BaseModel):
    created: int
    skipped: int
    errors: list[dict[str, object]]
