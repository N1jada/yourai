/**
 * API Types — Type definitions matching backend schemas
 */

// ============================================================================
// Common
// ============================================================================

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ApiError {
  detail: string;
  code?: string;
}

// ============================================================================
// Auth
// ============================================================================

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface User {
  id: string;
  tenant_id: string;
  email: string;
  given_name: string;
  family_name: string;
  role: "owner" | "admin" | "analyst" | "viewer";
  status: "active" | "inactive" | "suspended";
  created_at: string;
  last_login_at?: string;
}

// ============================================================================
// Conversations
// ============================================================================

export interface Conversation {
  id: string;
  tenant_id: string;
  user_id: string;
  title?: string;
  state: "ready" | "processing" | "error";
  created_at: string;
  updated_at: string;
}

export interface CreateConversationRequest {
  title?: string;
}

export interface UpdateConversationRequest {
  title?: string;
}

// ============================================================================
// Messages
// ============================================================================

export type MessageRole = "user" | "assistant" | "system";

export type MessageState =
  | "pending"
  | "streaming"
  | "success"
  | "error"
  | "cancelled";

export type ConfidenceLevel = "high" | "medium" | "low";

export interface Message {
  id: string;
  tenant_id: string;
  conversation_id: string;
  role: MessageRole;
  content: string;
  state: MessageState;
  confidence_level?: ConfidenceLevel;
  verification_result?: VerificationResult;
  file_attachments?: FileAttachment[];
  created_at: string;
  updated_at: string;
}

export interface SendMessageRequest {
  content: string;
  file_attachments?: string[]; // Document IDs
}

export interface VerificationResult {
  citations_checked: number;
  citations_verified: number;
  citations_removed: number;
  verified_citations: VerifiedCitation[];
  issues: string[];
}

export interface VerifiedCitation {
  citation_text: string;
  verification_status: "verified" | "removed" | "pending";
  reason?: string;
}

export interface FileAttachment {
  id: string;
  filename: string;
  size_bytes: number;
}

// ============================================================================
// Personas
// ============================================================================

export interface Persona {
  id: string;
  tenant_id: string;
  name: string;
  description?: string;
  system_instructions?: string;
  activated_skills: string[];
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface CreatePersonaRequest {
  name: string;
  description?: string;
  system_instructions?: string;
  activated_skills?: string[];
}

export interface UpdatePersonaRequest {
  name?: string;
  description?: string;
  system_instructions?: string;
  activated_skills?: string[];
  is_active?: boolean;
}

// ============================================================================
// Knowledge Base
// ============================================================================

export interface KnowledgeBase {
  id: string;
  tenant_id: string;
  name: string;
  description?: string;
  embedding_model: string;
  is_active: boolean;
  document_count: number;
  created_at: string;
  updated_at: string;
}

export interface Document {
  id: string;
  tenant_id: string;
  kb_id: string;
  title: string;
  source_type: "upload" | "url" | "api" | "manual";
  source_url?: string;
  mime_type: string;
  size_bytes: number;
  status: "pending" | "processing" | "ready" | "failed";
  error_message?: string;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface UploadDocumentRequest {
  kb_id: string;
  file: File;
  metadata?: Record<string, unknown>;
}
