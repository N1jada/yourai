/**
 * Request body types for API mutations.
 *
 * Source of truth: API_CONTRACTS.md Section 6.13
 */

import type {
  GuardrailStatus,
  KnowledgeBaseCategory,
  KnowledgeBaseSourceType,
  UserStatus,
} from "./enums";

// Auth
export interface LoginRequest {
  email: string;
  password: string;
}

export interface DevTokenRequest {
  user_id: string;
  tenant_id: string;
  email: string;
}

// Users
export interface CreateUser {
  email: string;
  given_name: string;
  family_name: string;
  job_role?: string;
  role_ids?: string[];
}

export interface UpdateUser {
  given_name?: string;
  family_name?: string;
  job_role?: string;
  status?: UserStatus;
  notification_preferences?: Record<string, unknown>;
}

export interface UpdateProfile {
  given_name?: string;
  family_name?: string;
  job_role?: string;
  notification_preferences?: Record<string, unknown>;
}

export interface AssignRoles {
  role_ids: string[];
}

export interface BulkInviteRequest {
  users: CreateUser[];
}

// Roles
export interface CreateRole {
  name: string;
  description?: string;
  permission_ids?: string[];
}

export interface UpdateRole {
  name?: string;
  description?: string;
  permission_ids?: string[];
}

// Tenant
export interface UpdateTenant {
  name?: string;
  industry_vertical?: string;
  branding_config?: Record<string, unknown>;
  ai_config?: Record<string, unknown>;
  news_feed_urls?: string[];
  external_source_integrations?: Record<string, unknown>[];
}

// Conversations
export interface CreateConversation {
  title?: string;
  template_id?: string;
}

export interface UpdateConversation {
  title?: string;
}

export interface SendMessage {
  content: string;
  persona_id?: string;
  attachments?: Record<string, unknown>[];
}

// Knowledge
export interface CreateKnowledgeBase {
  name: string;
  category: KnowledgeBaseCategory;
  source_type: KnowledgeBaseSourceType;
}

export interface SearchRequest {
  query: string;
  categories?: KnowledgeBaseCategory[];
  knowledge_base_ids?: string[];
  limit?: number;
  similarity_threshold?: number;
}

// Personas
export interface CreatePersona {
  name: string;
  description?: string;
  system_instructions?: string;
  activated_skills?: Record<string, unknown>[];
}

export interface UpdatePersona {
  name?: string;
  description?: string;
  system_instructions?: string;
  activated_skills?: Record<string, unknown>[];
}

// Guardrails
export interface CreateGuardrail {
  name: string;
  description?: string;
  configuration_rules?: Record<string, unknown>;
}

export interface UpdateGuardrail {
  name?: string;
  description?: string;
  status?: GuardrailStatus;
  configuration_rules?: Record<string, unknown>;
}

// Feedback
export interface CreateFeedback {
  rating: "up" | "down";
  comment?: string;
}
