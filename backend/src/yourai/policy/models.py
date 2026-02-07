"""Policy review ORM models."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

import uuid_utils
from sqlalchemy import Column, ForeignKey, Index, Table, UniqueConstraint, Uuid
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from yourai.core.database import Base, TenantScopedMixin

if TYPE_CHECKING:
    from yourai.core.models import User

# Association table for M:M relationship between PolicyDefinition and PolicyDefinitionTopic
policy_definition_topics_map = Table(
    "policy_definition_topics_map",
    Base.metadata,
    Column(
        "policy_definition_id",
        Uuid,
        ForeignKey("policy_definitions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "topic_id",
        Uuid,
        ForeignKey("policy_definition_topics.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class PolicyDefinitionGroup(TenantScopedMixin, Base):
    """Top-level organizational grouping for policy definitions.

    Examples: "Health & Safety", "Tenant Services", "Asset Management"
    """

    __tablename__ = "policy_definition_groups"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid_utils.uuid7)
    name: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[str | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Relationships
    definitions: Mapped[list[PolicyDefinition]] = relationship(
        back_populates="group",
        cascade="all, delete-orphan",
    )


class PolicyDefinitionTopic(TenantScopedMixin, Base):
    """Cross-cutting themes that can be associated with multiple policy definitions.

    Examples: "Fire Safety", "Data Protection", "Safeguarding"
    """

    __tablename__ = "policy_definition_topics"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid_utils.uuid7)
    name: Mapped[str] = mapped_column(nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Relationships (M:M)
    definitions: Mapped[list[PolicyDefinition]] = relationship(
        secondary=policy_definition_topics_map,
        back_populates="topics",
    )


class PolicyDefinition(TenantScopedMixin, Base):
    """Core ontology entry defining a policy type with compliance criteria.

    Each definition includes:
    - Scoring criteria (Green/Amber/Red thresholds)
    - Compliance criteria (required elements)
    - Required sections
    - Legislation references
    """

    __tablename__ = "policy_definitions"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid_utils.uuid7)
    name: Mapped[str] = mapped_column(nullable=False)
    uri: Mapped[str] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(nullable=False, default="active")
    group_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("policy_definition_groups.id", ondelete="SET NULL"),
        nullable=True,
    )
    description: Mapped[str | None] = mapped_column(nullable=True)
    is_required: Mapped[bool] = mapped_column(nullable=False, default=False)
    review_cycle: Mapped[str | None] = mapped_column(nullable=True)
    name_variants: Mapped[Any] = mapped_column(JSON, nullable=False, default=list)
    scoring_criteria: Mapped[Any] = mapped_column(JSON, nullable=False, default=dict)
    compliance_criteria: Mapped[Any] = mapped_column(JSON, nullable=False, default=dict)
    required_sections: Mapped[Any] = mapped_column(JSON, nullable=False, default=list)
    legislation_references: Mapped[Any] = mapped_column(JSON, nullable=False, default=list)
    last_regulatory_update_date: Mapped[datetime | None] = mapped_column(nullable=True)
    regulatory_change_flags: Mapped[Any] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime | None] = mapped_column(nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Relationships
    group: Mapped[PolicyDefinitionGroup | None] = relationship(back_populates="definitions")
    topics: Mapped[list[PolicyDefinitionTopic]] = relationship(
        secondary=policy_definition_topics_map,
        back_populates="definitions",
    )
    reviews: Mapped[list[PolicyReview]] = relationship(
        back_populates="policy_definition",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "uri", name="uq_policy_definitions_tenant_uri"),
        Index("ix_policy_definitions_group_id", "group_id"),
        Index("ix_policy_definitions_status", "status"),
    )


class PolicyReview(TenantScopedMixin, Base):
    """Record of a completed policy review.

    Links to the policy definition (if identified) and stores:
    - Review result (compliance assessment)
    - Citation verification results
    - Source document reference
    """

    __tablename__ = "policy_reviews"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid_utils.uuid7)
    request_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    policy_definition_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("policy_definitions.id", ondelete="SET NULL"),
        nullable=True,
    )
    state: Mapped[str] = mapped_column(nullable=False, default="pending")
    result: Mapped[Any] = mapped_column(JSON, nullable=True)
    source: Mapped[str | None] = mapped_column(nullable=True)
    citation_verification_result: Mapped[Any] = mapped_column(JSON, nullable=True)
    version: Mapped[int] = mapped_column(nullable=False, default=1)
    created_at: Mapped[datetime | None] = mapped_column(nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Relationships
    user: Mapped[User] = relationship()
    policy_definition: Mapped[PolicyDefinition | None] = relationship(back_populates="reviews")

    __table_args__ = (
        Index("ix_policy_reviews_user_id", "user_id"),
        Index("ix_policy_reviews_policy_definition_id", "policy_definition_id"),
        Index("ix_policy_reviews_state", "state"),
    )
