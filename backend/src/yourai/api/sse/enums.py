"""Enum types used by SSE events. Mirrors the PostgreSQL enum types."""

from enum import StrEnum


class ConversationState(StrEnum):
    PENDING = "pending"
    WAITING_FOR_REPLY = "waiting_for_reply"
    GENERATING_REPLY = "generating_reply"
    OUTPUTTING_REPLY = "outputting_reply"
    READY = "ready"


class MessageState(StrEnum):
    PENDING = "pending"
    SUCCESS = "success"
    ERROR = "error"
    CANCELLED = "cancelled"


class ConfidenceLevel(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class VerificationStatus(StrEnum):
    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    REMOVED = "removed"
    PRE_1963_DIGITISED = "pre_1963_digitised"


class PolicyReviewState(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    VERIFYING = "verifying"
    COMPLETE = "complete"
    ERROR = "error"
    CANCELLED = "cancelled"


class RegulatoryChangeType(StrEnum):
    NEW_LEGISLATION = "new_legislation"
    AMENDMENT = "amendment"
    NEW_REGULATORY_STANDARD = "new_regulatory_standard"
    CONSULTATION = "consultation"
