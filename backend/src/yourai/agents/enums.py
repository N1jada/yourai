"""Enumerations for agent-related models.

Ported from the database schema enum types defined in DATABASE_SCHEMA.sql.
"""

from __future__ import annotations

from enum import StrEnum


class ConversationState(StrEnum):
    """State machine for conversations."""

    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class MessageRole(StrEnum):
    """Message sender role in a conversation."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class MessageState(StrEnum):
    """Processing state of a message."""

    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ConfidenceLevel(StrEnum):
    """AI response confidence level."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class VerificationStatus(StrEnum):
    """Citation verification status."""

    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    FAILED = "failed"
    PENDING = "pending"


class AgentInvocationMode(StrEnum):
    """Mode of agent invocation."""

    CONVERSATION = "conversation"
    POLICY_REVIEW = "policy_review"
    ONE_SHOT = "one_shot"


class ModelTier(StrEnum):
    """Claude model tier used for an invocation."""

    HAIKU = "haiku"
    SONNET = "sonnet"
    OPUS = "opus"
