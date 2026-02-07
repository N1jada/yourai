"""SQLAlchemy 2.0 models for WP5 agent tables.

Models match the canonical schema in docs/architecture/DATABASE_SCHEMA.sql.
All tables are tenant-scoped with TenantScopedMixin except agent_invocation_events
(which inherits tenant isolation through its parent FK).

Uses dialect-agnostic types (JSON, DateTime, Uuid) for SQLite test compatibility.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)

import uuid_utils
from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from yourai.core.database import Base, TenantScopedMixin
from yourai.core.enums import (
    AgentInvocationMode,
    ConfidenceLevel,
    ConversationState,
    FeedbackRating,
    FeedbackReviewStatus,
    MessageRole,
    MessageState,
    ModelTier,
)


class Persona(TenantScopedMixin, Base):
    """Tenant-scoped persona (system prompt template)."""

    __tablename__ = "personas"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid_utils.uuid7)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    system_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    activated_skills: Mapped[list] = mapped_column(  # type: ignore[type-arg]
        JSON, nullable=False, default=list
    )
    usage_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=_utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=_utcnow)


class Conversation(TenantScopedMixin, Base):
    """Tenant-scoped conversation owned by a user."""

    __tablename__ = "conversations"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid_utils.uuid7)
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    state: Mapped[ConversationState] = mapped_column(
        Enum(ConversationState, name="conversation_state", create_type=False, values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        default=ConversationState.PENDING,
    )
    # NOTE: conversation_templates table not yet implemented (WP5 Session 2+)
    # For now, we store the ID but don't enforce FK constraint
    template_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=_utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=_utcnow)

    # Relationships
    messages: Mapped[list[Message]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at"
    )
    invocations: Mapped[list[AgentInvocation]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan"
    )


class Message(TenantScopedMixin, Base):
    """A message in a conversation (user or assistant)."""

    __tablename__ = "messages"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid_utils.uuid7)
    conversation_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )
    request_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    role: Mapped[MessageRole] = mapped_column(
        Enum(MessageRole, name="message_role", create_type=False, values_callable=lambda e: [m.value for m in e]),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    state: Mapped[MessageState] = mapped_column(
        Enum(MessageState, name="message_state", create_type=False, values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        default=MessageState.PENDING,
    )
    metadata_: Mapped[dict] = mapped_column(  # type: ignore[type-arg]
        "metadata", JSON, nullable=False, default=dict
    )
    file_attachments: Mapped[list] = mapped_column(  # type: ignore[type-arg]
        JSON, nullable=False, default=list
    )
    confidence_level: Mapped[ConfidenceLevel | None] = mapped_column(
        Enum(ConfidenceLevel, name="confidence_level", create_type=False, values_callable=lambda e: [m.value for m in e]),
        nullable=True,
    )
    verification_result: Mapped[dict | None] = mapped_column(  # type: ignore[type-arg]
        JSON, nullable=True
    )
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=_utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=_utcnow)

    # Relationships
    conversation: Mapped[Conversation] = relationship(back_populates="messages")


class AgentInvocation(TenantScopedMixin, Base):
    """A single agent invocation (tracks one user query through the agent pipeline)."""

    __tablename__ = "agent_invocations"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid_utils.uuid7)
    conversation_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=True
    )
    request_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    mode: Mapped[AgentInvocationMode] = mapped_column(
        Enum(AgentInvocationMode, name="agent_invocation_mode", create_type=False, values_callable=lambda e: [m.value for m in e]),
        nullable=False,
    )
    query: Mapped[str | None] = mapped_column(Text, nullable=True)
    persona_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("personas.id", ondelete="SET NULL"), nullable=True
    )
    context_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    state: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    attachments: Mapped[list] = mapped_column(  # type: ignore[type-arg]
        JSON, nullable=False, default=list
    )
    model_used: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_tier: Mapped[ModelTier | None] = mapped_column(
        Enum(ModelTier, name="model_tier", create_type=False, values_callable=lambda e: [m.value for m in e]),
        nullable=True,
    )
    cache_hit: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=_utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=_utcnow)

    # Relationships
    conversation: Mapped[Conversation | None] = relationship(back_populates="invocations")
    events: Mapped[list[AgentInvocationEvent]] = relationship(
        back_populates="invocation", cascade="all, delete-orphan"
    )


class AgentInvocationEvent(Base):
    """Event log for a single agent invocation (no TenantScopedMixin, inherits via FK)."""

    __tablename__ = "agent_invocation_events"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid_utils.uuid7)
    tenant_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    agent_invocation_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("agent_invocations.id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    payload: Mapped[dict] = mapped_column(  # type: ignore[type-arg]
        JSON, nullable=False, default=dict
    )
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=_utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=_utcnow)

    # Relationships
    invocation: Mapped[AgentInvocation] = relationship(back_populates="events")


class Feedback(TenantScopedMixin, Base):
    """User feedback on a message (thumbs up/down with optional comment)."""

    __tablename__ = "feedbacks"
    __table_args__ = (UniqueConstraint("message_id", "user_id", name="uq_feedbacks_message_user"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid_utils.uuid7)
    message_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("messages.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    rating: Mapped[FeedbackRating] = mapped_column(
        Enum(FeedbackRating, name="feedback_rating", create_type=False, values_callable=lambda e: [m.value for m in e]),
        nullable=False,
    )
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    review_status: Mapped[FeedbackReviewStatus] = mapped_column(
        Enum(FeedbackReviewStatus, name="feedback_review_status", create_type=False, values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        default=FeedbackReviewStatus.PENDING,
    )
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=_utcnow)


class SemanticCacheEntry(TenantScopedMixin, Base):
    """Semantic cache for query responses (embedding-based similarity matching)."""

    __tablename__ = "semantic_cache_entries"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid_utils.uuid7)
    query_embedding: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    response: Mapped[str] = mapped_column(Text, nullable=False)
    sources: Mapped[dict] = mapped_column(  # type: ignore[type-arg]
        JSON, nullable=False, default=list
    )
    ttl_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=3600)
    hit_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=_utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=_utcnow)
