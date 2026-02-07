/**
 * Conversation, Message, and Feedback types.
 *
 * Source of truth: API_CONTRACTS.md Section 6.5
 */

import type {
  ConfidenceLevel,
  ConversationState,
  FeedbackRating,
  FeedbackReviewStatus,
  MessageRole,
  MessageState,
} from "./enums";

export interface ConversationResponse {
  id: string;
  tenant_id: string;
  user_id: string;
  title: string | null;
  state: ConversationState;
  template_id: string | null;
  message_count: number;
  deleted_at: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface FeedbackResponse {
  id: string;
  message_id: string;
  user_id: string;
  rating: FeedbackRating;
  comment: string | null;
  review_status: FeedbackReviewStatus;
  created_at: string | null;
}

export interface MessageResponse {
  id: string;
  tenant_id: string;
  conversation_id: string;
  request_id: string | null;
  role: MessageRole;
  content: string;
  state: MessageState;
  metadata_: Record<string, unknown>;
  file_attachments: Record<string, unknown>[];
  confidence_level: ConfidenceLevel | null;
  verification_result: Record<string, unknown> | null;
  feedback: FeedbackResponse | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface ConversationTemplateResponse {
  id: string;
  tenant_id: string;
  name: string;
  description?: string;
  created_at?: string;
}
