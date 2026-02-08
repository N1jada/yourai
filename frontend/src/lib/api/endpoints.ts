/**
 * API Endpoints — Typed API methods for all backend routes
 */

import type { ApiClient } from "./client";
import type { LoginResponse } from "./types";
import type { Page } from "@/lib/types/common";
import type { TenantConfig } from "@/lib/types/tenant";
import type { UserResponse, RoleResponse, PermissionResponse, BulkInviteResult } from "@/lib/types/users";
import type {
  ConversationResponse,
  ConversationTemplateResponse,
  FeedbackResponse,
  MessageResponse,
} from "@/lib/types/conversations";
import type {
  KnowledgeBaseResponse,
  DocumentResponse,
  DocumentVersion,
  SearchResult,
} from "@/lib/types/knowledge";
import type { PersonaResponse } from "@/lib/types/personas";
import type { GuardrailResponse } from "@/lib/types/guardrails";
import type { HealthResponse } from "@/lib/types/health";
import type {
  LexOverviewResponse,
  LegislationSearchParams,
  LegislationSearchResponse,
  LegislationDetailResponse,
  HealthCheckResponse,
  ForcePrimaryResponse,
} from "@/lib/types/legislation";
import type {
  LoginRequest,
  CreateConversation,
  UpdateConversation,
  SendMessage,
  CreatePersona,
  UpdatePersona,
  CreateUser,
  UpdateUser,
  AssignRoles,
  BulkInviteRequest,
  CreateRole,
  UpdateRole,
  UpdateTenant,
  CreateKnowledgeBase,
  SearchRequest,
  CreateGuardrail,
  UpdateGuardrail,
  UpdateProfile,
  CreateFeedback,
} from "@/lib/types/requests";

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------

export class AuthApi {
  constructor(private client: ApiClient) {}

  async login(data: LoginRequest): Promise<LoginResponse> {
    return this.client.post("/api/v1/auth/login", data);
  }

  async logout(): Promise<void> {
    return this.client.post("/api/v1/auth/logout");
  }

  async getCurrentUser(): Promise<UserResponse> {
    return this.client.get("/api/v1/auth/me");
  }

  async refreshToken(): Promise<LoginResponse> {
    return this.client.post("/api/v1/auth/refresh");
  }
}

// ---------------------------------------------------------------------------
// Conversations
// ---------------------------------------------------------------------------

export class ConversationsApi {
  constructor(private client: ApiClient) {}

  async list(params?: { page?: number; page_size?: number }): Promise<Page<ConversationResponse>> {
    return this.client.get("/api/v1/conversations", params);
  }

  async create(data: CreateConversation): Promise<ConversationResponse> {
    return this.client.post("/api/v1/conversations", data);
  }

  async get(id: string): Promise<ConversationResponse> {
    return this.client.get(`/api/v1/conversations/${id}`);
  }

  async update(id: string, data: UpdateConversation): Promise<ConversationResponse> {
    return this.client.patch(`/api/v1/conversations/${id}`, data);
  }

  async delete(id: string): Promise<void> {
    return this.client.delete(`/api/v1/conversations/${id}`);
  }

  async cancel(id: string): Promise<void> {
    return this.client.post(`/api/v1/conversations/${id}/cancel`);
  }

  async exportConversation(id: string, format: "markdown" | "pdf" = "markdown"): Promise<Blob> {
    // Returns raw response for download
    return this.client.get(`/api/v1/conversations/${id}/export`, { format });
  }
}

// ---------------------------------------------------------------------------
// Messages
// ---------------------------------------------------------------------------

export class MessagesApi {
  constructor(private client: ApiClient) {}

  async list(
    conversationId: string,
    params?: { page?: number; page_size?: number },
  ): Promise<Page<MessageResponse>> {
    return this.client.get(
      `/api/v1/conversations/${conversationId}/messages`,
      params,
    );
  }

  async send(conversationId: string, data: SendMessage): Promise<MessageResponse> {
    return this.client.post(
      `/api/v1/conversations/${conversationId}/messages`,
      data,
    );
  }
}

// ---------------------------------------------------------------------------
// Feedback
// ---------------------------------------------------------------------------

export class FeedbackApi {
  constructor(private client: ApiClient) {}

  async submit(messageId: string, data: CreateFeedback): Promise<FeedbackResponse> {
    return this.client.post(`/api/v1/messages/${messageId}/feedback`, data);
  }
}

// ---------------------------------------------------------------------------
// Conversation Templates
// ---------------------------------------------------------------------------

export class TemplatesApi {
  constructor(private client: ApiClient) {}

  async list(): Promise<ConversationTemplateResponse[]> {
    return this.client.get("/api/v1/conversation-templates");
  }
}

// ---------------------------------------------------------------------------
// Personas
// ---------------------------------------------------------------------------

export class PersonasApi {
  constructor(private client: ApiClient) {}

  async list(params?: { page?: number; page_size?: number }): Promise<Page<PersonaResponse>> {
    return this.client.get("/api/v1/personas", params);
  }

  async create(data: CreatePersona): Promise<PersonaResponse> {
    return this.client.post("/api/v1/personas", data);
  }

  async get(id: string): Promise<PersonaResponse> {
    return this.client.get(`/api/v1/personas/${id}`);
  }

  async update(id: string, data: UpdatePersona): Promise<PersonaResponse> {
    return this.client.patch(`/api/v1/personas/${id}`, data);
  }

  async delete(id: string): Promise<void> {
    return this.client.delete(`/api/v1/personas/${id}`);
  }

  async duplicate(id: string): Promise<PersonaResponse> {
    return this.client.post(`/api/v1/personas/${id}/duplicate`);
  }
}

// ---------------------------------------------------------------------------
// Knowledge Base
// ---------------------------------------------------------------------------

export class KnowledgeBaseApi {
  constructor(private client: ApiClient) {}

  async list(params?: { page?: number; page_size?: number }): Promise<Page<KnowledgeBaseResponse>> {
    return this.client.get("/api/v1/knowledge-bases", params);
  }

  async create(data: CreateKnowledgeBase): Promise<KnowledgeBaseResponse> {
    return this.client.post("/api/v1/knowledge-bases", data);
  }

  async get(id: string): Promise<KnowledgeBaseResponse> {
    return this.client.get(`/api/v1/knowledge-bases/${id}`);
  }

  async delete(id: string): Promise<void> {
    return this.client.delete(`/api/v1/knowledge-bases/${id}`);
  }

  async search(data: SearchRequest): Promise<SearchResult[]> {
    return this.client.post("/api/v1/search", data);
  }
}

// ---------------------------------------------------------------------------
// Documents
// ---------------------------------------------------------------------------

export class DocumentsApi {
  constructor(private client: ApiClient) {}

  async list(
    kbId: string,
    params?: { page?: number; page_size?: number },
  ): Promise<Page<DocumentResponse>> {
    return this.client.get(`/api/v1/knowledge-bases/${kbId}/documents`, params);
  }

  async upload(kbId: string, file: File, metadata?: Record<string, unknown>): Promise<DocumentResponse> {
    const formData = new FormData();
    formData.append("file", file);
    if (metadata) {
      formData.append("metadata", JSON.stringify(metadata));
    }

    return this.client.postFormData(
      `/api/v1/knowledge-bases/${kbId}/documents`,
      formData,
    );
  }

  async get(_kbId: string, documentId: string): Promise<DocumentResponse> {
    return this.client.get(`/api/v1/documents/${documentId}`);
  }

  async delete(_kbId: string, documentId: string): Promise<void> {
    return this.client.delete(`/api/v1/documents/${documentId}`);
  }

  async getVersions(_kbId: string, documentId: string): Promise<DocumentVersion[]> {
    return this.client.get(`/api/v1/documents/${documentId}/versions`);
  }
}

// ---------------------------------------------------------------------------
// Users (Admin)
// ---------------------------------------------------------------------------

export class UsersApi {
  constructor(private client: ApiClient) {}

  async list(params?: {
    page?: number;
    page_size?: number;
    search?: string;
    status?: string;
  }): Promise<Page<UserResponse>> {
    return this.client.get("/api/v1/users", params);
  }

  async create(data: CreateUser): Promise<UserResponse> {
    return this.client.post("/api/v1/users", data);
  }

  async get(id: string): Promise<UserResponse> {
    return this.client.get(`/api/v1/users/${id}`);
  }

  async update(id: string, data: UpdateUser): Promise<UserResponse> {
    return this.client.patch(`/api/v1/users/${id}`, data);
  }

  async delete(id: string): Promise<void> {
    return this.client.delete(`/api/v1/users/${id}`);
  }

  async assignRoles(id: string, data: AssignRoles): Promise<UserResponse> {
    return this.client.put(`/api/v1/users/${id}/roles`, data);
  }

  async bulkInvite(data: BulkInviteRequest): Promise<BulkInviteResult> {
    return this.client.post("/api/v1/users/bulk-invite", data);
  }
}

// ---------------------------------------------------------------------------
// Roles (Admin)
// ---------------------------------------------------------------------------

export class RolesApi {
  constructor(private client: ApiClient) {}

  async list(): Promise<RoleResponse[]> {
    return this.client.get("/api/v1/roles");
  }

  async create(data: CreateRole): Promise<RoleResponse> {
    return this.client.post("/api/v1/roles", data);
  }

  async get(id: string): Promise<RoleResponse> {
    return this.client.get(`/api/v1/roles/${id}`);
  }

  async update(id: string, data: UpdateRole): Promise<RoleResponse> {
    return this.client.patch(`/api/v1/roles/${id}`, data);
  }

  async delete(id: string): Promise<void> {
    return this.client.delete(`/api/v1/roles/${id}`);
  }
}

// ---------------------------------------------------------------------------
// Permissions
// ---------------------------------------------------------------------------

export class PermissionsApi {
  constructor(private client: ApiClient) {}

  async list(): Promise<PermissionResponse[]> {
    return this.client.get("/api/v1/permissions");
  }
}

// ---------------------------------------------------------------------------
// Guardrails (Admin)
// ---------------------------------------------------------------------------

export class GuardrailsApi {
  constructor(private client: ApiClient) {}

  async list(params?: { page?: number; page_size?: number }): Promise<Page<GuardrailResponse>> {
    return this.client.get("/api/v1/guardrails", params);
  }

  async create(data: CreateGuardrail): Promise<GuardrailResponse> {
    return this.client.post("/api/v1/guardrails", data);
  }

  async get(id: string): Promise<GuardrailResponse> {
    return this.client.get(`/api/v1/guardrails/${id}`);
  }

  async update(id: string, data: UpdateGuardrail): Promise<GuardrailResponse> {
    return this.client.patch(`/api/v1/guardrails/${id}`, data);
  }

  async delete(id: string): Promise<void> {
    return this.client.delete(`/api/v1/guardrails/${id}`);
  }
}

// ---------------------------------------------------------------------------
// Legislation Admin
// ---------------------------------------------------------------------------

export class LegislationAdminApi {
  constructor(private client: ApiClient) {}

  async getOverview(): Promise<LexOverviewResponse> {
    return this.client.get("/api/v1/admin/legislation/overview");
  }

  async search(params: LegislationSearchParams): Promise<LegislationSearchResponse> {
    return this.client.post("/api/v1/admin/legislation/search", params);
  }

  async getDetail(type: string, year: number, number: number): Promise<LegislationDetailResponse> {
    return this.client.get(`/api/v1/admin/legislation/detail/${type}/${year}/${number}`);
  }

  async checkHealth(): Promise<HealthCheckResponse> {
    return this.client.post("/api/v1/admin/legislation/health-check");
  }

  async forcePrimary(): Promise<ForcePrimaryResponse> {
    return this.client.post("/api/v1/admin/legislation/force-primary");
  }
}

// ---------------------------------------------------------------------------
// Activity Logs (Admin)
// ---------------------------------------------------------------------------

export interface ActivityLogFilters {
  page?: number;
  page_size?: number;
  tag?: string;
  user_id?: string;
  date_from?: string;
  date_to?: string;
}

export interface ActivityLogResponse {
  id: string;
  tenant_id: string;
  user_id: string | null;
  user_name: string | null;
  action: string;
  detail: string | null;
  tags: string[];
  created_at: string | null;
}

export class ActivityLogsApi {
  constructor(private client: ApiClient) {}

  async list(params?: ActivityLogFilters): Promise<Page<ActivityLogResponse>> {
    return this.client.get("/api/v1/activity-logs", params as Record<string, unknown>);
  }

  async exportCsv(params?: Omit<ActivityLogFilters, "page" | "page_size">): Promise<string> {
    return this.client.get("/api/v1/activity-logs/export", params as Record<string, unknown>);
  }
}

// ---------------------------------------------------------------------------
// Tenant
// ---------------------------------------------------------------------------

export class TenantApi {
  constructor(private client: ApiClient) {}

  async getConfig(): Promise<TenantConfig> {
    return this.client.get("/api/v1/tenants/me");
  }

  async update(data: UpdateTenant): Promise<TenantConfig> {
    return this.client.patch("/api/v1/tenants/me", data);
  }

  async getBranding(slug: string): Promise<TenantConfig> {
    return this.client.get(`/api/v1/tenants/by-slug/${slug}/branding`);
  }
}

// ---------------------------------------------------------------------------
// Profile
// ---------------------------------------------------------------------------

export class ProfileApi {
  constructor(private client: ApiClient) {}

  async get(): Promise<UserResponse> {
    return this.client.get("/api/v1/profile");
  }

  async update(data: UpdateProfile): Promise<UserResponse> {
    return this.client.patch("/api/v1/profile", data);
  }
}

// ---------------------------------------------------------------------------
// Health
// ---------------------------------------------------------------------------

export class HealthApi {
  constructor(private client: ApiClient) {}

  async check(): Promise<HealthResponse> {
    return this.client.get("/api/v1/health");
  }
}

// ---------------------------------------------------------------------------
// Root API
// ---------------------------------------------------------------------------

export class Api {
  public auth: AuthApi;
  public conversations: ConversationsApi;
  public messages: MessagesApi;
  public feedback: FeedbackApi;
  public templates: TemplatesApi;
  public personas: PersonasApi;
  public knowledgeBases: KnowledgeBaseApi;
  public documents: DocumentsApi;
  public users: UsersApi;
  public roles: RolesApi;
  public permissions: PermissionsApi;
  public guardrails: GuardrailsApi;
  public legislation: LegislationAdminApi;
  public activityLogs: ActivityLogsApi;
  public tenant: TenantApi;
  public profile: ProfileApi;
  public health: HealthApi;

  constructor(client: ApiClient) {
    this.auth = new AuthApi(client);
    this.conversations = new ConversationsApi(client);
    this.messages = new MessagesApi(client);
    this.feedback = new FeedbackApi(client);
    this.templates = new TemplatesApi(client);
    this.personas = new PersonasApi(client);
    this.knowledgeBases = new KnowledgeBaseApi(client);
    this.documents = new DocumentsApi(client);
    this.users = new UsersApi(client);
    this.roles = new RolesApi(client);
    this.permissions = new PermissionsApi(client);
    this.guardrails = new GuardrailsApi(client);
    this.legislation = new LegislationAdminApi(client);
    this.activityLogs = new ActivityLogsApi(client);
    this.tenant = new TenantApi(client);
    this.profile = new ProfileApi(client);
    this.health = new HealthApi(client);
  }
}
