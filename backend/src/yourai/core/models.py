"""SQLAlchemy 2.0 models for WP1 core tables.

Models match the canonical schema in docs/architecture/DATABASE_SCHEMA.sql.
Platform tables (tenants, permissions) have no tenant_id and no RLS.
Tenant-scoped tables (users, roles) use TenantScopedMixin.
Join tables (role_permissions, user_roles) use composite primary keys.

Note: Uses dialect-agnostic types (JSON, DateTime, Uuid) so models work with
both PostgreSQL (production) and SQLite (unit tests). On PostgreSQL, JSON maps
to JSONB and Uuid maps to the native UUID type.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

import uuid_utils
from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from yourai.core.database import Base, TenantScopedMixin
from yourai.core.enums import SubscriptionTier, UserStatus


class Tenant(Base):
    """Platform-level tenant. No tenant_id, no RLS."""

    __tablename__ = "tenants"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid_utils.uuid7)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    slug: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    industry_vertical: Mapped[str | None] = mapped_column(Text, nullable=True)
    branding_config: Mapped[dict] = mapped_column(  # type: ignore[type-arg]
        JSON, nullable=False, default=dict
    )
    subscription_tier: Mapped[SubscriptionTier] = mapped_column(
        String, nullable=False, default=SubscriptionTier.STARTER
    )
    credit_limit: Mapped[Decimal] = mapped_column(
        Numeric(12, 4), nullable=False, default=Decimal("0")
    )
    billing_period_start: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    billing_period_end: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    news_feed_urls: Mapped[list] = mapped_column(  # type: ignore[type-arg]
        JSON, nullable=False, default=list
    )
    external_source_integrations: Mapped[list] = mapped_column(  # type: ignore[type-arg]
        JSON, nullable=False, default=list
    )
    ai_config: Mapped[dict] = mapped_column(  # type: ignore[type-arg]
        JSON, nullable=False, default=dict
    )
    vector_namespace: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    users: Mapped[list[User]] = relationship(back_populates="tenant")
    roles: Mapped[list[Role]] = relationship(back_populates="tenant")


class Permission(Base):
    """Platform-level permission. No tenant_id, no RLS."""

    __tablename__ = "permissions"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid_utils.uuid7)
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class RolePermission(Base):
    """Join table: role <-> permission. No tenant_id (parent provides isolation)."""

    __tablename__ = "role_permissions"

    role_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True,
    )
    permission_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("permissions.id", ondelete="CASCADE"),
        primary_key=True,
    )


class UserRole(Base):
    """Join table: user <-> role. No tenant_id (parent provides isolation)."""

    __tablename__ = "user_roles"

    user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    role_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True,
    )


class User(TenantScopedMixin, Base):
    """Tenant-scoped user. RLS via tenant_id."""

    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("tenant_id", "email", name="idx_users_tenant_email"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid_utils.uuid7)
    email: Mapped[str] = mapped_column(Text, nullable=False)
    given_name: Mapped[str] = mapped_column(Text, nullable=False)
    family_name: Mapped[str] = mapped_column(Text, nullable=False)
    job_role: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[UserStatus] = mapped_column(
        String, nullable=False, default=UserStatus.PENDING
    )
    last_active_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    notification_preferences: Mapped[dict] = mapped_column(  # type: ignore[type-arg]
        JSON, nullable=False, default=dict
    )
    data_deletion_requested_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    tenant: Mapped[Tenant] = relationship(back_populates="users")
    roles: Mapped[list[Role]] = relationship(
        secondary="user_roles", back_populates="users", lazy="selectin"
    )


class Role(TenantScopedMixin, Base):
    """Tenant-scoped role. RLS via tenant_id."""

    __tablename__ = "roles"
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_roles_tenant_name"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid_utils.uuid7)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    tenant: Mapped[Tenant] = relationship(back_populates="roles")
    permissions: Mapped[list[Permission]] = relationship(
        secondary="role_permissions", lazy="selectin"
    )
    users: Mapped[list[User]] = relationship(
        secondary="user_roles", back_populates="roles"
    )
