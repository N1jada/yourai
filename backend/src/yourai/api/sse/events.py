"""Typed SSE event models matching the API contracts spec (Section 4).

Every event model has an `event_type` literal field used as the SSE `event:` line.
All models are Pydantic v2 BaseModels for serialisation to JSON `data:` lines.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from yourai.api.sse.enums import (  # noqa: TCH001 — Pydantic needs these at runtime
    ConfidenceLevel,
    ConversationState,
    MessageState,
    PolicyReviewState,
    RegulatoryChangeType,
    VerificationStatus,
)

# ---------------------------------------------------------------------------
# 4.1 Conversation Stream Events
# ---------------------------------------------------------------------------

# -- Agent lifecycle events --


class AgentStartEvent(BaseModel):
    """Sub-agent has begun processing."""

    event_type: Literal["agent_start"] = "agent_start"
    agent_name: str
    task_description: str


class AgentProgressEvent(BaseModel):
    """Sub-agent progress update (thinking/searching)."""

    event_type: Literal["agent_progress"] = "agent_progress"
    agent_name: str
    status_text: str


class AgentCompleteEvent(BaseModel):
    """Sub-agent has finished processing."""

    event_type: Literal["agent_complete"] = "agent_complete"
    agent_name: str
    duration_ms: int


# -- Content events --


class ContentDeltaEvent(BaseModel):
    """Incremental text chunk from the AI response."""

    event_type: Literal["content_delta"] = "content_delta"
    text: str


# -- Source/citation events --


class LegalSourceEvent(BaseModel):
    """Legislation reference discovered during response generation."""

    event_type: Literal["legal_source"] = "legal_source"
    act_name: str
    section: str
    uri: str
    verification_status: VerificationStatus


class CaseLawSourceEvent(BaseModel):
    """Court case reference discovered."""

    event_type: Literal["case_law_source"] = "case_law_source"
    case_name: str
    citation: str
    court: str
    date: str


class AnnotationEvent(BaseModel):
    """Expert commentary/annotation discovered on a cited source."""

    event_type: Literal["annotation"] = "annotation"
    content: str
    contributor: str
    type: str


class CompanyPolicySourceEvent(BaseModel):
    """Internal policy document reference discovered."""

    event_type: Literal["company_policy_source"] = "company_policy_source"
    document_name: str
    section: str


class ParliamentarySourceEvent(BaseModel):
    """Parliamentary data reference discovered (Hansard, Written Questions, etc.)."""

    event_type: Literal["parliamentary_source"] = "parliamentary_source"
    type: str
    reference: str
    date: str
    member: str | None = None


# -- Quality events --


class ConfidenceUpdateEvent(BaseModel):
    """Response confidence level determined/updated."""

    event_type: Literal["confidence_update"] = "confidence_update"
    level: ConfidenceLevel
    reason: str


class UsageMetricsEvent(BaseModel):
    """Token usage for a model call within this invocation."""

    event_type: Literal["usage_metrics"] = "usage_metrics"
    model: str
    input_tokens: int
    output_tokens: int


class VerificationResultEvent(BaseModel):
    """Final citation verification outcome."""

    event_type: Literal["verification_result"] = "verification_result"
    citations_checked: int
    citations_verified: int
    issues: list[str]


# -- Lifecycle events --


class MessageStateEvent(BaseModel):
    """Message state transition."""

    event_type: Literal["message_state"] = "message_state"
    message_id: str
    state: MessageState


class MessageCompleteEvent(BaseModel):
    """Response generation finished. Final message content is set."""

    event_type: Literal["message_complete"] = "message_complete"
    message_id: str


class ConversationStateEvent(BaseModel):
    """Conversation state machine transition."""

    event_type: Literal["conversation_state"] = "conversation_state"
    state: ConversationState


class ConversationCancelledEvent(BaseModel):
    """Invocation was cancelled by the user."""

    event_type: Literal["conversation_cancelled"] = "conversation_cancelled"


class ErrorEvent(BaseModel):
    """Error during processing."""

    event_type: Literal["error"] = "error"
    code: str
    message: str
    recoverable: bool


# ---------------------------------------------------------------------------
# 4.2 Policy Review Stream Events
# ---------------------------------------------------------------------------


class PolicyReviewStatusEvent(BaseModel):
    """Policy review progress update."""

    event_type: Literal["policy_review_status"] = "policy_review_status"
    state: PolicyReviewState
    status_text: str


class PolicyReviewCitationProgressEvent(BaseModel):
    """Incremental citation verification progress during policy review."""

    event_type: Literal["policy_review_citation_progress"] = "policy_review_citation_progress"
    citations_checked_so_far: int
    total_citations: int


class PolicyReviewCompleteEvent(BaseModel):
    """Policy review finished. Full result is available via GET."""

    event_type: Literal["policy_review_complete"] = "policy_review_complete"
    review_id: str


class PolicyReviewFailedEvent(BaseModel):
    """Policy review encountered an unrecoverable error."""

    event_type: Literal["policy_review_failed"] = "policy_review_failed"
    error_code: str
    message: str


# ---------------------------------------------------------------------------
# 4.3 User-Level Push Events
# ---------------------------------------------------------------------------


class ConversationTitleUpdatedEvent(BaseModel):
    event_type: Literal["conversation_title_updated"] = "conversation_title_updated"
    conversation_id: str
    title: str


class ConversationTitleUpdatingEvent(BaseModel):
    event_type: Literal["conversation_title_updating"] = "conversation_title_updating"
    conversation_id: str


class PolicyReviewCreatedEvent(BaseModel):
    event_type: Literal["policy_review_created"] = "policy_review_created"
    review_id: str
    state: PolicyReviewState


class RegulatoryChangeAlertEvent(BaseModel):
    event_type: Literal["regulatory_change_alert"] = "regulatory_change_alert"
    alert_id: str
    summary: str
    change_type: RegulatoryChangeType


class CreditUsageWarningEvent(BaseModel):
    event_type: Literal["credit_usage_warning"] = "credit_usage_warning"
    percentage_used: float
    credits_remaining: float


# -- Lex Ingestion events --


class IngestionStartedEvent(BaseModel):
    event_type: Literal["ingestion_started"] = "ingestion_started"
    job_id: str
    mode: str


class IngestionProgressEvent(BaseModel):
    event_type: Literal["ingestion_progress"] = "ingestion_progress"
    job_id: str
    message: str


class IngestionCompletedEvent(BaseModel):
    event_type: Literal["ingestion_completed"] = "ingestion_completed"
    job_id: str
    result: dict[str, object]


class IngestionFailedEvent(BaseModel):
    event_type: Literal["ingestion_failed"] = "ingestion_failed"
    job_id: str
    error: str


# ---------------------------------------------------------------------------
# Union types
# ---------------------------------------------------------------------------

StreamEvent = (
    AgentStartEvent
    | AgentProgressEvent
    | AgentCompleteEvent
    | ContentDeltaEvent
    | LegalSourceEvent
    | CaseLawSourceEvent
    | AnnotationEvent
    | CompanyPolicySourceEvent
    | ParliamentarySourceEvent
    | ConfidenceUpdateEvent
    | UsageMetricsEvent
    | VerificationResultEvent
    | MessageStateEvent
    | MessageCompleteEvent
    | ConversationStateEvent
    | ConversationCancelledEvent
    | ErrorEvent
    | PolicyReviewStatusEvent
    | PolicyReviewCitationProgressEvent
    | PolicyReviewCompleteEvent
    | PolicyReviewFailedEvent
)

UserPushEvent = (
    ConversationTitleUpdatedEvent
    | ConversationTitleUpdatingEvent
    | PolicyReviewCreatedEvent
    | RegulatoryChangeAlertEvent
    | CreditUsageWarningEvent
    | IngestionStartedEvent
    | IngestionProgressEvent
    | IngestionCompletedEvent
    | IngestionFailedEvent
)

AnySSEEvent = StreamEvent | UserPushEvent
