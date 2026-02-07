/**
 * SSE event types — All 26 event interfaces for real-time streaming.
 *
 * Source of truth: API_CONTRACTS.md Section 4 + backend/src/yourai/api/sse/events.py
 */

import type {
  ConfidenceLevel,
  ConversationState,
  MessageState,
  PolicyReviewState,
  RegulatoryChangeType,
  VerificationStatus,
} from "./enums";

// ---------------------------------------------------------------------------
// 4.1 Conversation Stream Events
// ---------------------------------------------------------------------------

// -- Agent lifecycle --

export interface AgentStartEvent {
  event_type: "agent_start";
  agent_name: string;
  task_description: string;
}

export interface AgentProgressEvent {
  event_type: "agent_progress";
  agent_name: string;
  status_text: string;
}

export interface AgentCompleteEvent {
  event_type: "agent_complete";
  agent_name: string;
  duration_ms: number;
}

// -- Content --

export interface ContentDeltaEvent {
  event_type: "content_delta";
  text: string;
}

// -- Source/citation --

export interface LegalSourceEvent {
  event_type: "legal_source";
  act_name: string;
  section: string;
  uri: string;
  verification_status: VerificationStatus;
}

export interface CaseLawSourceEvent {
  event_type: "case_law_source";
  case_name: string;
  citation: string;
  court: string;
  date: string;
}

export interface AnnotationEvent {
  event_type: "annotation";
  content: string;
  contributor: string;
  type: string;
}

export interface CompanyPolicySourceEvent {
  event_type: "company_policy_source";
  document_name: string;
  section: string;
}

export interface ParliamentarySourceEvent {
  event_type: "parliamentary_source";
  type: string;
  reference: string;
  date: string;
  member?: string;
}

// -- Quality --

export interface ConfidenceUpdateEvent {
  event_type: "confidence_update";
  level: ConfidenceLevel;
  reason: string;
}

export interface UsageMetricsEvent {
  event_type: "usage_metrics";
  model: string;
  input_tokens: number;
  output_tokens: number;
}

export interface VerificationResultEvent {
  event_type: "verification_result";
  citations_checked: number;
  citations_verified: number;
  issues: string[];
}

// -- Lifecycle --

export interface MessageStateEvent {
  event_type: "message_state";
  message_id: string;
  state: MessageState;
}

export interface MessageCompleteEvent {
  event_type: "message_complete";
  message_id: string;
}

export interface ConversationStateEvent {
  event_type: "conversation_state";
  state: ConversationState;
}

export interface ConversationCancelledEvent {
  event_type: "conversation_cancelled";
}

export interface ErrorEvent {
  event_type: "error";
  code: string;
  message: string;
  recoverable: boolean;
}

// ---------------------------------------------------------------------------
// 4.2 Policy Review Stream Events
// ---------------------------------------------------------------------------

export interface PolicyReviewStatusEvent {
  event_type: "policy_review_status";
  state: PolicyReviewState;
  status_text: string;
}

export interface PolicyReviewCitationProgressEvent {
  event_type: "policy_review_citation_progress";
  citations_checked_so_far: number;
  total_citations: number;
}

export interface PolicyReviewCompleteEvent {
  event_type: "policy_review_complete";
  review_id: string;
}

export interface PolicyReviewFailedEvent {
  event_type: "policy_review_failed";
  error_code: string;
  message: string;
}

// ---------------------------------------------------------------------------
// 4.3 User-Level Push Events
// ---------------------------------------------------------------------------

export interface ConversationTitleUpdatedEvent {
  event_type: "conversation_title_updated";
  conversation_id: string;
  title: string;
}

export interface ConversationTitleUpdatingEvent {
  event_type: "conversation_title_updating";
  conversation_id: string;
}

export interface PolicyReviewCreatedEvent {
  event_type: "policy_review_created";
  review_id: string;
  state: PolicyReviewState;
}

export interface RegulatoryChangeAlertEvent {
  event_type: "regulatory_change_alert";
  alert_id: string;
  summary: string;
  change_type: RegulatoryChangeType;
}

export interface CreditUsageWarningEvent {
  event_type: "credit_usage_warning";
  percentage_used: number;
  credits_remaining: number;
}

// ---------------------------------------------------------------------------
// Union types
// ---------------------------------------------------------------------------

export type StreamEvent =
  | AgentStartEvent
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
  | PolicyReviewFailedEvent;

export type UserPushEvent =
  | ConversationTitleUpdatedEvent
  | ConversationTitleUpdatingEvent
  | PolicyReviewCreatedEvent
  | RegulatoryChangeAlertEvent
  | CreditUsageWarningEvent;

export type AnySSEEvent = StreamEvent | UserPushEvent;

/** SSE event type discriminator values. */
export type SSEEventType = AnySSEEvent["event_type"];
