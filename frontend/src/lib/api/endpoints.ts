/**
 * API Endpoints — Typed API methods for all backend routes
 */

import type { ApiClient } from "./client";
import type {
  Page,
  LoginRequest,
  LoginResponse,
  User,
  Conversation,
  CreateConversationRequest,
  UpdateConversationRequest,
  Message,
  SendMessageRequest,
  Persona,
  CreatePersonaRequest,
  UpdatePersonaRequest,
  KnowledgeBase,
  Document,
} from "./types";

/**
 * Authentication endpoints
 */
export class AuthApi {
  constructor(private client: ApiClient) {}

  async login(data: LoginRequest): Promise<LoginResponse> {
    return this.client.post("/api/v1/auth/login", data);
  }

  async logout(): Promise<void> {
    return this.client.post("/api/v1/auth/logout");
  }

  async getCurrentUser(): Promise<User> {
    return this.client.get("/api/v1/auth/me");
  }

  async refreshToken(): Promise<LoginResponse> {
    return this.client.post("/api/v1/auth/refresh");
  }
}

/**
 * Conversation endpoints
 */
export class ConversationsApi {
  constructor(private client: ApiClient) {}

  async list(params?: { page?: number; page_size?: number }): Promise<Page<Conversation>> {
    return this.client.get("/api/v1/conversations", params);
  }

  async create(data: CreateConversationRequest): Promise<Conversation> {
    return this.client.post("/api/v1/conversations", data);
  }

  async get(id: string): Promise<Conversation> {
    return this.client.get(`/api/v1/conversations/${id}`);
  }

  async update(id: string, data: UpdateConversationRequest): Promise<Conversation> {
    return this.client.patch(`/api/v1/conversations/${id}`, data);
  }

  async delete(id: string): Promise<void> {
    return this.client.delete(`/api/v1/conversations/${id}`);
  }
}

/**
 * Message endpoints
 */
export class MessagesApi {
  constructor(private client: ApiClient) {}

  async list(
    conversationId: string,
    params?: { page?: number; page_size?: number },
  ): Promise<Page<Message>> {
    return this.client.get(
      `/api/v1/conversations/${conversationId}/messages`,
      params,
    );
  }

  async send(conversationId: string, data: SendMessageRequest): Promise<Message> {
    return this.client.post(
      `/api/v1/conversations/${conversationId}/messages`,
      data,
    );
  }
}

/**
 * Persona endpoints
 */
export class PersonasApi {
  constructor(private client: ApiClient) {}

  async list(): Promise<Persona[]> {
    return this.client.get("/api/v1/personas");
  }

  async create(data: CreatePersonaRequest): Promise<Persona> {
    return this.client.post("/api/v1/personas", data);
  }

  async get(id: string): Promise<Persona> {
    return this.client.get(`/api/v1/personas/${id}`);
  }

  async update(id: string, data: UpdatePersonaRequest): Promise<Persona> {
    return this.client.patch(`/api/v1/personas/${id}`, data);
  }

  async delete(id: string): Promise<void> {
    return this.client.delete(`/api/v1/personas/${id}`);
  }
}

/**
 * Knowledge Base endpoints
 */
export class KnowledgeBaseApi {
  constructor(private client: ApiClient) {}

  async list(params?: { page?: number; page_size?: number }): Promise<Page<KnowledgeBase>> {
    return this.client.get("/api/v1/knowledge-bases", params);
  }

  async get(id: string): Promise<KnowledgeBase> {
    return this.client.get(`/api/v1/knowledge-bases/${id}`);
  }
}

/**
 * Document endpoints
 */
export class DocumentsApi {
  constructor(private client: ApiClient) {}

  async list(
    kbId: string,
    params?: { page?: number; page_size?: number },
  ): Promise<Page<Document>> {
    return this.client.get(`/api/v1/knowledge-bases/${kbId}/documents`, params);
  }

  async upload(kbId: string, file: File, metadata?: Record<string, unknown>): Promise<Document> {
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

  async get(kbId: string, documentId: string): Promise<Document> {
    return this.client.get(`/api/v1/knowledge-bases/${kbId}/documents/${documentId}`);
  }

  async delete(kbId: string, documentId: string): Promise<void> {
    return this.client.delete(`/api/v1/knowledge-bases/${kbId}/documents/${documentId}`);
  }
}

/**
 * Root API class that aggregates all endpoint groups
 */
export class Api {
  public auth: AuthApi;
  public conversations: ConversationsApi;
  public messages: MessagesApi;
  public personas: PersonasApi;
  public knowledgeBases: KnowledgeBaseApi;
  public documents: DocumentsApi;

  constructor(client: ApiClient) {
    this.auth = new AuthApi(client);
    this.conversations = new ConversationsApi(client);
    this.messages = new MessagesApi(client);
    this.personas = new PersonasApi(client);
    this.knowledgeBases = new KnowledgeBaseApi(client);
    this.documents = new DocumentsApi(client);
  }
}
