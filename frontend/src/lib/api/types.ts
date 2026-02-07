/**
 * API Types — Re-exports from @/lib/types for backward compatibility.
 *
 * New code should import from "@/lib/types" or specific sub-modules directly.
 */

// Re-export common types
export type { Page, ErrorResponse } from "@/lib/types/common";

// Re-export enums
export type {
  ConversationState,
  MessageRole,
  MessageState,
  ConfidenceLevel,
  UserStatus,
  DocumentProcessingState,
  KnowledgeBaseCategory,
  KnowledgeBaseSourceType,
  FeedbackRating,
  FeedbackReviewStatus,
  GuardrailStatus,
} from "@/lib/types/enums";

// Re-export auth
export type { TokenPair } from "@/lib/types/tenant";

// Re-export request types
export type {
  LoginRequest,
  CreateConversation as CreateConversationRequest,
  UpdateConversation as UpdateConversationRequest,
  SendMessage as SendMessageRequest,
  CreatePersona as CreatePersonaRequest,
  UpdatePersona as UpdatePersonaRequest,
  CreateKnowledgeBase as CreateKnowledgeBaseRequest,
} from "@/lib/types/requests";

// Re-export response types with aliases matching old names
export type { UserResponse as User } from "@/lib/types/users";
export type {
  ConversationResponse as Conversation,
  MessageResponse as Message,
  FeedbackResponse,
  ConversationTemplateResponse,
} from "@/lib/types/conversations";
export type {
  KnowledgeBaseResponse as KnowledgeBase,
  DocumentResponse as Document,
  SearchResult,
} from "@/lib/types/knowledge";
export type { PersonaResponse as Persona } from "@/lib/types/personas";
export type { GuardrailResponse } from "@/lib/types/guardrails";
export type { HealthResponse } from "@/lib/types/health";

// LoginResponse kept here since it's a frontend-specific shape (includes user)
export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  expires_in: number;
  user: import("@/lib/types/users").UserResponse;
}
