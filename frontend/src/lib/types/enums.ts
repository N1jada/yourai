/**
 * Enum types — Literal string unions matching backend StrEnums.
 *
 * Source of truth: API_CONTRACTS.md Section 6.1
 */

// Core
export type SubscriptionTier = "starter" | "professional" | "enterprise";
export type UserStatus = "pending" | "active" | "disabled" | "deleted";

// Conversations
export type ConversationState =
  | "pending"
  | "waiting_for_reply"
  | "generating_reply"
  | "outputting_reply"
  | "ready";
export type MessageRole = "user" | "assistant";
export type MessageState = "pending" | "success" | "error" | "cancelled";
export type ConfidenceLevel = "high" | "medium" | "low";

// Documents & Knowledge
export type KnowledgeBaseCategory =
  | "legislation"
  | "case_law"
  | "explanatory_notes"
  | "amendments"
  | "company_policy"
  | "sector_knowledge"
  | "parliamentary";
export type KnowledgeBaseSourceType =
  | "lex_api"
  | "uploaded"
  | "catalog"
  | "parliament_mcp";
export type DocumentProcessingState =
  | "uploaded"
  | "validating"
  | "extracting_text"
  | "chunking"
  | "contextualising"
  | "embedding"
  | "indexing"
  | "ready"
  | "failed";

// Verification & Citation
export type VerificationStatus =
  | "verified"
  | "unverified"
  | "removed"
  | "pre_1963_digitised";

// Agent
export type AgentInvocationMode = "conversation" | "policy_review";
export type ModelTier = "haiku" | "sonnet" | "opus";

// Guardrails
export type GuardrailStatus =
  | "creating"
  | "updating"
  | "versioning"
  | "ready"
  | "failed"
  | "deleting";

// Policy
export type PolicyReviewState =
  | "pending"
  | "processing"
  | "verifying"
  | "complete"
  | "error"
  | "cancelled";
export type ReviewCycle = "annual" | "monthly" | "quarterly";
export type RAGRating = "green" | "amber" | "red";
export type RegulatoryChangeType =
  | "new_legislation"
  | "amendment"
  | "new_regulatory_standard"
  | "consultation";
export type AlertStatus = "pending" | "acknowledged" | "dismissed" | "actioned";

// Billing
export type BillingEventType = "credit" | "usage" | "adjustment";
export type BillingFeature =
  | "conversation"
  | "policy_review"
  | "title_generation"
  | "regulatory_monitoring";

// Activity
export type ActivityLogTag = "user" | "system" | "security" | "ai";

// Feedback
export type FeedbackRating = "up" | "down";
export type FeedbackReviewStatus = "pending" | "reviewed" | "actioned";
