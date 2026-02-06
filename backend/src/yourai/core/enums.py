"""Shared StrEnum definitions mirroring PostgreSQL enum types.

These enums are the single Python source of truth for all enum values.
They MUST match the PostgreSQL enums defined in DATABASE_SCHEMA.sql.
"""

from enum import StrEnum


class SubscriptionTier(StrEnum):
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class UserStatus(StrEnum):
    PENDING = "pending"
    ACTIVE = "active"
    DISABLED = "disabled"
    DELETED = "deleted"


class ConversationState(StrEnum):
    PENDING = "pending"
    WAITING_FOR_REPLY = "waiting_for_reply"
    GENERATING_REPLY = "generating_reply"
    OUTPUTTING_REPLY = "outputting_reply"
    READY = "ready"


class MessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"


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


class AgentInvocationMode(StrEnum):
    CONVERSATION = "conversation"
    POLICY_REVIEW = "policy_review"


class ModelTier(StrEnum):
    HAIKU = "haiku"
    SONNET = "sonnet"
    OPUS = "opus"


class KnowledgeBaseCategory(StrEnum):
    LEGISLATION = "legislation"
    CASE_LAW = "case_law"
    EXPLANATORY_NOTES = "explanatory_notes"
    AMENDMENTS = "amendments"
    COMPANY_POLICY = "company_policy"
    SECTOR_KNOWLEDGE = "sector_knowledge"
    PARLIAMENTARY = "parliamentary"


class KnowledgeBaseSourceType(StrEnum):
    LEX_API = "lex_api"
    UPLOADED = "uploaded"
    CATALOG = "catalog"
    PARLIAMENT_MCP = "parliament_mcp"


class DocumentProcessingState(StrEnum):
    UPLOADED = "uploaded"
    VALIDATING = "validating"
    EXTRACTING_TEXT = "extracting_text"
    CHUNKING = "chunking"
    CONTEXTUALISING = "contextualising"
    EMBEDDING = "embedding"
    INDEXING = "indexing"
    READY = "ready"
    FAILED = "failed"


class GuardrailStatus(StrEnum):
    CREATING = "creating"
    UPDATING = "updating"
    VERSIONING = "versioning"
    READY = "ready"
    FAILED = "failed"
    DELETING = "deleting"


class ReviewCycle(StrEnum):
    ANNUAL = "annual"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"


class PolicyReviewState(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    VERIFYING = "verifying"
    COMPLETE = "complete"
    ERROR = "error"
    CANCELLED = "cancelled"


class RAGRating(StrEnum):
    GREEN = "green"
    AMBER = "amber"
    RED = "red"


class RegulatoryChangeType(StrEnum):
    NEW_LEGISLATION = "new_legislation"
    AMENDMENT = "amendment"
    NEW_REGULATORY_STANDARD = "new_regulatory_standard"
    CONSULTATION = "consultation"


class AlertStatus(StrEnum):
    PENDING = "pending"
    ACKNOWLEDGED = "acknowledged"
    DISMISSED = "dismissed"
    ACTIONED = "actioned"


class BillingEventType(StrEnum):
    CREDIT = "credit"
    USAGE = "usage"
    ADJUSTMENT = "adjustment"


class BillingFeature(StrEnum):
    CONVERSATION = "conversation"
    POLICY_REVIEW = "policy_review"
    TITLE_GENERATION = "title_generation"
    REGULATORY_MONITORING = "regulatory_monitoring"


class ActivityLogTag(StrEnum):
    USER = "user"
    SYSTEM = "system"
    SECURITY = "security"
    AI = "ai"


class FeedbackRating(StrEnum):
    UP = "up"
    DOWN = "down"


class FeedbackReviewStatus(StrEnum):
    PENDING = "pending"
    REVIEWED = "reviewed"
    ACTIONED = "actioned"
