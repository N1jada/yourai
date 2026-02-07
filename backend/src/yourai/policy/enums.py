"""Policy-related enums."""

from __future__ import annotations

from enum import StrEnum


class ReviewCycle(StrEnum):
    """Policy review cycle frequency."""

    ANNUAL = "annual"
    QUARTERLY = "quarterly"
    MONTHLY = "monthly"


class PolicyReviewState(StrEnum):
    """Policy review workflow states."""

    PENDING = "pending"
    PROCESSING = "processing"
    VERIFYING = "verifying"
    COMPLETE = "complete"
    ERROR = "error"
    CANCELLED = "cancelled"


class PolicyStatus(StrEnum):
    """Policy definition active status."""

    ACTIVE = "active"
    INACTIVE = "inactive"


class RAGRating(StrEnum):
    """Red/Amber/Green compliance rating."""

    GREEN = "green"
    AMBER = "amber"
    RED = "red"
