# YourAI — API Contracts

> **Purpose**: Defines every interface that crosses a work-package boundary.
> All Python service classes, REST endpoints, SSE events, and Celery tasks
> defined here are binding contracts. Implementations MUST match these
> signatures. TypeScript equivalents are provided for all types the frontend
> consumes.
>
> **Canonical schema**: `docs/architecture/DATABASE_SCHEMA.sql`
> **Technology decisions**: `docs/architecture/TECH_DECISIONS.md`

---

## Table of Contents

1. [Shared Types & Conventions](#1-shared-types--conventions)
2. [Python Service Interfaces](#2-python-service-interfaces)
3. [REST API Endpoints](#3-rest-api-endpoints)
4. [SSE Event Definitions](#4-sse-event-definitions)
5. [Celery Task Signatures](#5-celery-task-signatures)
6. [TypeScript Type Definitions](#6-typescript-type-definitions)

---

## 1. Shared Types & Conventions

### 1.1 Common Conventions

| Convention | Value |
|---|---|
| API prefix | `/api/v1/` |
| Auth | Bearer JWT in `Authorization` header |
| Tenant scoping | `tenant_id` extracted from JWT claims, never from request params |
| Content type | `application/json` (except file upload: `multipart/form-data`, SSE: `text/event-stream`) |
| ID format | UUID (v7 preferred, v4 accepted) |
| Timestamps | ISO 8601 with timezone (`2025-06-15T14:30:00Z`) |
| Pagination | Offset-based: `?page=1&page_size=20` |
| Sorting | `?sort_by=created_at&sort_order=desc` |
| British English | All user-facing strings, error messages, AI prompts |

### 1.2 Pagination Wrapper

```python
from pydantic import BaseModel
from typing import Generic, TypeVar

T = TypeVar("T")

class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    has_next: bool
```

### 1.3 Error Response

```python
class ErrorResponse(BaseModel):
    code: str            # Machine-readable: "tenant_not_found", "permission_denied"
    message: str         # Human-readable British English
    detail: dict | None = None  # Optional structured context
```

Standard HTTP status mapping:

| Status | Code | Usage |
|---|---|---|
| 400 | `validation_error` | Request body / param validation failure |
| 401 | `unauthorised` | Missing or invalid JWT |
| 403 | `permission_denied` | Valid JWT but insufficient permissions |
| 404 | `not_found` | Resource does not exist (or not in tenant) |
| 409 | `conflict` | Duplicate resource (e.g. duplicate email) |
| 422 | `unprocessable_entity` | Semantically invalid (e.g. invalid state transition) |
| 423 | `user_not_active` | Account pending / disabled / deleted |
| 429 | `rate_limited` | Too many requests; `Retry-After` header set |
| 500 | `internal_error` | Unexpected server error |
| 502 | `upstream_error` | Lex API / Anthropic API failure |
| 503 | `service_unavailable` | Maintenance or overload |

### 1.4 Shared Enums (Python)

These mirror the PostgreSQL enum types in `DATABASE_SCHEMA.sql`:

```python
from enum import StrEnum

class SubscriptionTier(StrEnum):
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"

class UserStatus(StrEnum):
    PENDING = "pending"
    ACTIVE = "active"
    DISABLED = "disabled"
    DELETED = "deleted"

class ConversationState(StrEnum):
    PENDING = "pending"
    WAITING_FOR_REPLY = "waiting_for_reply"
    GENERATING_REPLY = "generating_reply"
    OUTPUTTING_REPLY = "outputting_reply"
    READY = "ready"

class MessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"

class MessageState(StrEnum):
    PENDING = "pending"
    SUCCESS = "success"
    ERROR = "error"
    CANCELLED = "cancelled"

class ConfidenceLevel(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class VerificationStatus(StrEnum):
    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    REMOVED = "removed"
    PRE_1963_DIGITISED = "pre_1963_digitised"

class AgentInvocationMode(StrEnum):
    CONVERSATION = "conversation"
    POLICY_REVIEW = "policy_review"

class ModelTier(StrEnum):
    HAIKU = "haiku"
    SONNET = "sonnet"
    OPUS = "opus"

class KnowledgeBaseCategory(StrEnum):
    LEGISLATION = "legislation"
    CASE_LAW = "case_law"
    EXPLANATORY_NOTES = "explanatory_notes"
    AMENDMENTS = "amendments"
    COMPANY_POLICY = "company_policy"
    SECTOR_KNOWLEDGE = "sector_knowledge"
    PARLIAMENTARY = "parliamentary"

class KnowledgeBaseSourceType(StrEnum):
    LEX_API = "lex_api"
    UPLOADED = "uploaded"
    CATALOG = "catalog"
    PARLIAMENT_MCP = "parliament_mcp"

class DocumentProcessingState(StrEnum):
    UPLOADED = "uploaded"
    VALIDATING = "validating"
    EXTRACTING_TEXT = "extracting_text"
    CHUNKING = "chunking"
    CONTEXTUALISING = "contextualising"
    EMBEDDING = "embedding"
    INDEXING = "indexing"
    READY = "ready"
    FAILED = "failed"

class GuardrailStatus(StrEnum):
    CREATING = "creating"
    UPDATING = "updating"
    VERSIONING = "versioning"
    READY = "ready"
    FAILED = "failed"
    DELETING = "deleting"

class ReviewCycle(StrEnum):
    ANNUAL = "annual"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"

class PolicyReviewState(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    VERIFYING = "verifying"
    COMPLETE = "complete"
    ERROR = "error"
    CANCELLED = "cancelled"

class RAGRating(StrEnum):
    GREEN = "green"
    AMBER = "amber"
    RED = "red"

class RegulatoryChangeType(StrEnum):
    NEW_LEGISLATION = "new_legislation"
    AMENDMENT = "amendment"
    NEW_REGULATORY_STANDARD = "new_regulatory_standard"
    CONSULTATION = "consultation"

class AlertStatus(StrEnum):
    PENDING = "pending"
    ACKNOWLEDGED = "acknowledged"
    DISMISSED = "dismissed"
    ACTIONED = "actioned"

class BillingEventType(StrEnum):
    CREDIT = "credit"
    USAGE = "usage"
    ADJUSTMENT = "adjustment"

class BillingFeature(StrEnum):
    CONVERSATION = "conversation"
    POLICY_REVIEW = "policy_review"
    TITLE_GENERATION = "title_generation"
    REGULATORY_MONITORING = "regulatory_monitoring"

class ActivityLogTag(StrEnum):
    USER = "user"
    SYSTEM = "system"
    SECURITY = "security"
    AI = "ai"

class FeedbackRating(StrEnum):
    UP = "up"
    DOWN = "down"

class FeedbackReviewStatus(StrEnum):
    PENDING = "pending"
    REVIEWED = "reviewed"
    ACTIONED = "actioned"
```

---

## 2. Python Service Interfaces

These are the cross-WP service classes. Each WP implements its own services;
the signatures below are the contracts that consuming WPs depend on.

### 2.1 WP1 — Core Platform Services

**Provider**: `backend/src/yourai/core/`
**Consumed by**: WP3, WP5, WP7 (via API)

#### 2.1.1 TenantService

```python
# core/tenant.py
from uuid import UUID
from pydantic import BaseModel
from datetime import datetime

class BrandingConfig(BaseModel):
    logo_url: str | None = None
    favicon_url: str | None = None
    app_name: str | None = None
    primary_colour: str | None = None
    secondary_colour: str | None = None
    custom_domain: str | None = None
    disclaimer_text: str | None = None

class AIConfig(BaseModel):
    confidence_thresholds: dict | None = None
    topic_restrictions: list[str] | None = None
    model_overrides: dict | None = None

class TenantConfig(BaseModel):
    id: UUID
    name: str
    slug: str
    industry_vertical: str | None
    branding: BrandingConfig
    ai_config: AIConfig
    subscription_tier: SubscriptionTier
    credit_limit: float
    billing_period_start: datetime | None
    billing_period_end: datetime | None
    is_active: bool
    news_feed_urls: list[str]
    external_source_integrations: list[dict]
    vector_namespace: str | None

class TenantService:
    async def get_tenant(self, tenant_id: UUID) -> TenantConfig:
        """Return full tenant configuration. Raises 404 if not found."""
        ...

    async def get_branding(self, tenant_id: UUID) -> BrandingConfig:
        """Return branding config only. Safe for unauthenticated pre-login use."""
        ...

    async def update_tenant(self, tenant_id: UUID, data: UpdateTenant) -> TenantConfig:
        """Update tenant settings. Requires platform_admin or tenant admin."""
        ...
```

#### 2.1.2 AuthService

```python
# core/auth.py
from pydantic import BaseModel

class TokenClaims(BaseModel):
    sub: str           # User ID from IdP
    email: str
    tenant_id: UUID
    exp: int           # Expiry timestamp

class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int    # Seconds

class AuthService:
    async def verify_token(self, token: str) -> TokenClaims:
        """Validate JWT signature, expiry, claims. Raises 401 on failure."""
        ...

    async def get_current_user(self, token: str) -> "UserResponse":
        """Verify token, then load the full User record. Raises 423 if not active."""
        ...

    async def refresh_token(self, refresh_token: str) -> TokenPair:
        """Exchange refresh token for new token pair. Raises 401 if expired."""
        ...
```

#### 2.1.3 UserService

```python
# core/users.py
from pydantic import BaseModel, EmailStr
from fastapi import UploadFile

class UserFilters(BaseModel):
    search: str | None = None       # Matches name or email
    status: UserStatus | None = None
    role_id: UUID | None = None
    page: int = 1
    page_size: int = 20

class CreateUser(BaseModel):
    email: EmailStr
    given_name: str
    family_name: str
    job_role: str | None = None
    role_ids: list[UUID] | None = None

class UpdateUser(BaseModel):
    given_name: str | None = None
    family_name: str | None = None
    job_role: str | None = None
    status: UserStatus | None = None
    notification_preferences: dict | None = None

class UserResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    email: str
    given_name: str
    family_name: str
    job_role: str | None
    status: UserStatus
    last_active_at: datetime | None
    notification_preferences: dict
    roles: list["RoleResponse"]
    created_at: datetime
    updated_at: datetime

class BulkInviteResult(BaseModel):
    created: int
    skipped: int       # Already exist
    errors: list[dict] # Row-level errors

class UserService:
    async def get_user(self, user_id: UUID, tenant_id: UUID) -> UserResponse:
        ...

    async def list_users(
        self, tenant_id: UUID, filters: UserFilters
    ) -> Page[UserResponse]:
        ...

    async def create_user(
        self, tenant_id: UUID, data: CreateUser
    ) -> UserResponse:
        ...

    async def update_user(
        self, user_id: UUID, tenant_id: UUID, data: UpdateUser
    ) -> UserResponse:
        ...

    async def delete_user(self, user_id: UUID, tenant_id: UUID) -> None:
        """Soft delete: sets status=deleted, deleted_at=now.
        Triggers async data erasure job."""
        ...

    async def bulk_invite(
        self, tenant_id: UUID, csv_file: UploadFile
    ) -> BulkInviteResult:
        """CSV columns: email, given_name, family_name, role"""
        ...
```

#### 2.1.4 RoleService & PermissionChecker

```python
# core/roles.py
class RoleResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    description: str | None
    permissions: list["PermissionResponse"]
    created_at: datetime

class PermissionResponse(BaseModel):
    id: UUID
    name: str
    description: str | None

class CreateRole(BaseModel):
    name: str
    description: str | None = None
    permission_ids: list[UUID] | None = None

class RoleService:
    async def list_roles(self, tenant_id: UUID) -> list[RoleResponse]:
        ...

    async def create_role(
        self, tenant_id: UUID, data: CreateRole
    ) -> RoleResponse:
        ...

    async def update_role(
        self, role_id: UUID, tenant_id: UUID, data: "UpdateRole"
    ) -> RoleResponse:
        ...

    async def delete_role(self, role_id: UUID, tenant_id: UUID) -> None:
        ...

    async def assign_roles_to_user(
        self, user_id: UUID, tenant_id: UUID, role_ids: list[UUID]
    ) -> UserResponse:
        """Replace all roles for the user."""
        ...

class PermissionChecker:
    async def check(self, user_id: UUID, permission: str) -> bool:
        """Return True if user has the permission via any assigned role."""
        ...

    async def require(self, user_id: UUID, permission: str) -> None:
        """Raise HTTPException(403) if user lacks the permission."""
        ...
```

#### 2.1.5 Middleware Dependencies

```python
# core/middleware.py — FastAPI dependency functions
from fastapi import Request, Depends
from typing import Callable

async def get_current_tenant(request: Request) -> TenantConfig:
    """Extract tenant_id from JWT, load tenant, set RLS context.
    Called via Depends() on every tenant-scoped endpoint.
    Side effect: executes SET LOCAL app.current_tenant_id = '<uuid>'."""
    ...

async def get_current_user(request: Request) -> UserResponse:
    """Verify JWT, load user record, check user is active.
    Raises 401 (invalid token), 423 (user not active)."""
    ...

def require_permission(permission: str) -> Callable:
    """Returns a FastAPI dependency that raises 403 if the current user
    does not have the specified permission."""
    ...
```

---

### 2.2 WP3 — Knowledge & Search Services

**Provider**: `backend/src/yourai/knowledge/`
**Consumed by**: WP5 (SearchService), WP7 (via API)

#### 2.2.1 KnowledgeBaseService

```python
# knowledge/knowledge_base.py
class KnowledgeBaseResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    category: KnowledgeBaseCategory
    source_type: KnowledgeBaseSourceType
    document_count: int       # Computed
    ready_document_count: int # Computed: documents in 'ready' state
    created_at: datetime
    updated_at: datetime

class CreateKnowledgeBase(BaseModel):
    name: str
    category: KnowledgeBaseCategory
    source_type: KnowledgeBaseSourceType

class KnowledgeBaseService:
    async def list_knowledge_bases(
        self, tenant_id: UUID
    ) -> list[KnowledgeBaseResponse]:
        ...

    async def create_knowledge_base(
        self, tenant_id: UUID, data: CreateKnowledgeBase
    ) -> KnowledgeBaseResponse:
        ...

    async def get_knowledge_base(
        self, knowledge_base_id: UUID, tenant_id: UUID
    ) -> KnowledgeBaseResponse:
        ...

    async def delete_knowledge_base(
        self, knowledge_base_id: UUID, tenant_id: UUID
    ) -> None:
        """Cascade deletes all documents, chunks, and Qdrant vectors."""
        ...

    async def sync_knowledge_base(
        self, knowledge_base_id: UUID, tenant_id: UUID
    ) -> None:
        """Trigger async sync for catalog-type knowledge bases."""
        ...
```

#### 2.2.2 DocumentService

```python
# knowledge/documents.py
from fastapi import UploadFile

class DocumentResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    knowledge_base_id: UUID
    name: str
    document_uri: str
    source_uri: str | None
    mime_type: str | None
    byte_size: int | None
    hash: str | None
    processing_state: DocumentProcessingState
    version_number: int
    previous_version_id: UUID | None
    metadata: dict
    chunk_count: int      # Computed
    retry_count: int
    last_error_message: str | None
    dead_letter: bool
    created_at: datetime
    updated_at: datetime

class DocumentVersion(BaseModel):
    id: UUID
    name: str
    version_number: int
    processing_state: DocumentProcessingState
    byte_size: int | None
    created_at: datetime

class DocumentFilters(BaseModel):
    processing_state: DocumentProcessingState | None = None
    dead_letter: bool | None = None
    search: str | None = None
    page: int = 1
    page_size: int = 20

class DocumentService:
    async def upload(
        self,
        file: UploadFile,
        knowledge_base_id: UUID,
        tenant_id: UUID,
    ) -> DocumentResponse:
        """Validate file (type, size), store, create DB record, enqueue
        processing pipeline. Returns immediately with state=uploaded."""
        ...

    async def get_document(
        self, document_id: UUID, tenant_id: UUID
    ) -> DocumentResponse:
        ...

    async def get_status(
        self, document_id: UUID, tenant_id: UUID
    ) -> DocumentProcessingState:
        ...

    async def list_documents(
        self, knowledge_base_id: UUID, tenant_id: UUID, filters: DocumentFilters
    ) -> Page[DocumentResponse]:
        ...

    async def delete_document(
        self, document_id: UUID, tenant_id: UUID
    ) -> None:
        """Delete DB records, chunks, and Qdrant vectors."""
        ...

    async def get_versions(
        self, document_id: UUID, tenant_id: UUID
    ) -> list[DocumentVersion]:
        ...

    async def retry_failed(
        self, document_id: UUID, tenant_id: UUID
    ) -> DocumentResponse:
        """Reset dead_letter=false, retry_count=0, re-enqueue processing."""
        ...
```

#### 2.2.3 SearchService

```python
# knowledge/search.py
class SearchResult(BaseModel):
    """Single search hit returned to the AI engine or UI."""
    chunk_id: UUID
    document_id: UUID
    document_name: str
    document_uri: str
    knowledge_base_category: KnowledgeBaseCategory
    chunk_index: int
    content: str
    contextual_prefix: str | None
    score: float               # Combined RRF + reranker score
    source_uri: str | None
    metadata: dict             # Document-level metadata

class VectorResult(BaseModel):
    chunk_id: UUID
    document_id: UUID
    score: float
    content: str

class KeywordResult(BaseModel):
    chunk_id: UUID
    document_id: UUID
    score: float
    content: str

class SearchRequest(BaseModel):
    query: str
    categories: list[KnowledgeBaseCategory] | None = None
    knowledge_base_ids: list[UUID] | None = None
    limit: int = 10
    similarity_threshold: float = 0.4

class SearchService:
    async def hybrid_search(
        self,
        query: str,
        tenant_id: UUID,
        categories: list[KnowledgeBaseCategory] | None = None,
        knowledge_base_ids: list[UUID] | None = None,
        limit: int = 10,
        similarity_threshold: float = 0.4,
    ) -> list[SearchResult]:
        """Full hybrid pipeline: embed → vector search → BM25 → RRF → rerank.
        Always scoped to tenant's Qdrant collection: tenant_{tenant_id}_documents."""
        ...

    async def vector_search(
        self,
        query: str,
        tenant_id: UUID,
        limit: int = 200,
    ) -> list[VectorResult]:
        """Raw vector similarity search. Used internally by hybrid_search."""
        ...

    async def keyword_search(
        self,
        query: str,
        tenant_id: UUID,
        limit: int = 200,
    ) -> list[KeywordResult]:
        """BM25 keyword search via Qdrant payload index."""
        ...
```

---

### 2.3 WP5 — AI Engine Services

**Provider**: `backend/src/yourai/agents/`
**Consumed by**: WP7 (via API)

#### 2.3.1 AgentEngine

```python
# agents/invocation.py
from collections.abc import AsyncGenerator

class Attachment(BaseModel):
    filename: str
    content_type: str
    data: bytes

class AgentEngine:
    async def invoke(
        self,
        message: str,
        conversation_id: UUID,
        tenant_id: UUID,
        user_id: UUID,
        persona_id: UUID | None = None,
        attachments: list[Attachment] | None = None,
    ) -> AsyncGenerator["StreamEvent", None]:
        """Main entry point. Creates an agent_invocation record, runs the
        multi-agent pipeline (router → orchestrator → workers → verification),
        and yields typed streaming events.

        The caller iterates this generator to produce SSE events."""
        ...

    async def cancel(self, invocation_id: UUID, tenant_id: UUID) -> None:
        """Cancel an in-flight invocation. Sets state to 'cancelled',
        stops generation, emits a final cancelled event."""
        ...
```

#### 2.3.2 ConversationService

```python
# agents/conversations.py
class ConversationResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    user_id: UUID
    title: str | None
    state: ConversationState
    template_id: UUID | None
    message_count: int    # Computed
    created_at: datetime
    updated_at: datetime

class CreateConversation(BaseModel):
    template_id: UUID | None = None

class UpdateConversation(BaseModel):
    title: str | None = None

class MessageResponse(BaseModel):
    id: UUID
    conversation_id: UUID
    request_id: UUID | None
    role: MessageRole
    content: str
    state: MessageState
    metadata: dict
    file_attachments: list[dict]
    confidence_level: ConfidenceLevel | None
    verification_result: dict | None
    feedback: "FeedbackResponse | None"   # Populated if current user left feedback
    created_at: datetime

class SendMessage(BaseModel):
    content: str
    persona_id: UUID | None = None
    attachments: list[dict] | None = None  # File references

class ConversationService:
    async def list_conversations(
        self, user_id: UUID, tenant_id: UUID, page: int = 1, page_size: int = 50
    ) -> Page[ConversationResponse]:
        """List user's conversations, newest first. Excludes soft-deleted."""
        ...

    async def create_conversation(
        self, user_id: UUID, tenant_id: UUID, data: CreateConversation
    ) -> ConversationResponse:
        ...

    async def get_conversation(
        self, conversation_id: UUID, tenant_id: UUID
    ) -> ConversationResponse:
        ...

    async def update_conversation(
        self, conversation_id: UUID, tenant_id: UUID, data: UpdateConversation
    ) -> ConversationResponse:
        ...

    async def delete_conversation(
        self, conversation_id: UUID, tenant_id: UUID
    ) -> None:
        """Soft delete: sets deleted_at=now."""
        ...

    async def list_messages(
        self, conversation_id: UUID, tenant_id: UUID, page: int = 1, page_size: int = 50
    ) -> Page[MessageResponse]:
        """Return messages in chronological order."""
        ...

    async def send_message(
        self, conversation_id: UUID, tenant_id: UUID, user_id: UUID, data: SendMessage
    ) -> MessageResponse:
        """Persist user message, then invoke AgentEngine. Returns the user
        message immediately; the assistant response streams via SSE."""
        ...
```

#### 2.3.3 PolicyReviewService

```python
# agents/policy_review.py
class PolicyReviewResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    request_id: UUID | None
    user_id: UUID
    policy_definition_id: UUID | None
    state: PolicyReviewState
    result: dict | None            # Structured review output when complete
    source: str | None
    citation_verification_result: dict | None
    version: int
    created_at: datetime
    updated_at: datetime

class CreatePolicyReview(BaseModel):
    policy_definition_id: UUID | None = None
    # File uploaded via multipart, not in JSON body

class PolicyReviewFilters(BaseModel):
    state: PolicyReviewState | None = None
    policy_definition_id: UUID | None = None
    page: int = 1
    page_size: int = 20

class PolicyReviewService:
    async def create_review(
        self,
        tenant_id: UUID,
        user_id: UUID,
        file: UploadFile,
        policy_definition_id: UUID | None = None,
    ) -> PolicyReviewResponse:
        """Upload policy document and start review pipeline.
        Returns immediately with state=pending."""
        ...

    async def get_review(
        self, review_id: UUID, tenant_id: UUID
    ) -> PolicyReviewResponse:
        ...

    async def list_reviews(
        self, tenant_id: UUID, filters: PolicyReviewFilters
    ) -> Page[PolicyReviewResponse]:
        ...

    async def cancel_review(
        self, review_id: UUID, tenant_id: UUID
    ) -> PolicyReviewResponse:
        ...

    async def stream_review(
        self, review_id: UUID, tenant_id: UUID
    ) -> AsyncGenerator["StreamEvent", None]:
        """SSE stream for policy review progress."""
        ...
```

#### 2.3.4 PersonaService

```python
# agents/personas.py
class PersonaResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    description: str | None
    system_instructions: str | None
    activated_skills: list[dict]
    usage_count: int
    created_at: datetime
    updated_at: datetime

class CreatePersona(BaseModel):
    name: str
    description: str | None = None
    system_instructions: str | None = None
    activated_skills: list[dict] | None = None

class UpdatePersona(BaseModel):
    name: str | None = None
    description: str | None = None
    system_instructions: str | None = None
    activated_skills: list[dict] | None = None

class PersonaService:
    async def list_personas(self, tenant_id: UUID) -> list[PersonaResponse]:
        ...

    async def create_persona(
        self, tenant_id: UUID, data: CreatePersona
    ) -> PersonaResponse:
        ...

    async def get_persona(
        self, persona_id: UUID, tenant_id: UUID
    ) -> PersonaResponse:
        ...

    async def update_persona(
        self, persona_id: UUID, tenant_id: UUID, data: UpdatePersona
    ) -> PersonaResponse:
        ...

    async def delete_persona(
        self, persona_id: UUID, tenant_id: UUID
    ) -> None:
        ...
```

#### 2.3.5 FeedbackService

```python
# agents/feedback.py
class FeedbackResponse(BaseModel):
    id: UUID
    message_id: UUID
    user_id: UUID
    rating: FeedbackRating
    comment: str | None
    review_status: FeedbackReviewStatus
    created_at: datetime

class CreateFeedback(BaseModel):
    rating: FeedbackRating
    comment: str | None = None

class FeedbackService:
    async def submit_feedback(
        self,
        message_id: UUID,
        user_id: UUID,
        tenant_id: UUID,
        data: CreateFeedback,
    ) -> FeedbackResponse:
        """Create or update feedback for a message. One feedback per user per message."""
        ...
```

---

## 3. REST API Endpoints

All endpoints require Bearer JWT unless marked **(public)**.
Tenant-scoped endpoints use `Depends(get_current_tenant)` and `Depends(get_current_user)`.

### 3.1 Auth — WP1

| Method | Path | Request | Response | Permission | Notes |
|---|---|---|---|---|---|
| `GET` | `/api/v1/auth/callback` | OAuth2 callback params | `TokenPair` | public | PKCE flow completion |
| `POST` | `/api/v1/auth/refresh` | `{ refresh_token: str }` | `TokenPair` | public | Silent token refresh |
| `POST` | `/api/v1/auth/logout` | — | `204 No Content` | authenticated | Invalidate session |

### 3.2 Tenants — WP1

| Method | Path | Request | Response | Permission | Notes |
|---|---|---|---|---|---|
| `GET` | `/api/v1/tenants/current` | — | `TenantConfig` | authenticated | Full config for current tenant |
| `PATCH` | `/api/v1/tenants/current` | `UpdateTenant` | `TenantConfig` | `update_tenant_settings` | Admin only |
| `GET` | `/api/v1/tenants/by-slug/{slug}/branding` | — | `BrandingConfig` | public | Pre-login branding |

```python
class UpdateTenant(BaseModel):
    name: str | None = None
    industry_vertical: str | None = None
    branding_config: dict | None = None
    ai_config: dict | None = None
    news_feed_urls: list[str] | None = None
    external_source_integrations: list[dict] | None = None
```

### 3.3 Users — WP1

| Method | Path | Request | Response | Permission | Notes |
|---|---|---|---|---|---|
| `GET` | `/api/v1/users` | `UserFilters` (query) | `Page[UserResponse]` | `list_users` | |
| `POST` | `/api/v1/users` | `CreateUser` | `UserResponse` | `create_user` | |
| `GET` | `/api/v1/users/{id}` | — | `UserResponse` | `view_user` | |
| `PATCH` | `/api/v1/users/{id}` | `UpdateUser` | `UserResponse` | `update_user_profile` | |
| `DELETE` | `/api/v1/users/{id}` | — | `204 No Content` | `delete_user` | Soft delete + erasure job |
| `POST` | `/api/v1/users/bulk-invite` | `multipart/form-data` (CSV) | `BulkInviteResult` | `create_user` | |
| `GET` | `/api/v1/users/me` | — | `UserResponse` | authenticated | Current user profile |
| `PATCH` | `/api/v1/users/me` | `UpdateProfile` | `UserResponse` | authenticated | Own profile only |
| `POST` | `/api/v1/users/me/data-export` | — | `202 Accepted` | authenticated | GDPR Subject Access Request |
| `POST` | `/api/v1/users/me/deletion-request` | — | `204 No Content` | authenticated | GDPR Right to Erasure |
| `GET` | `/api/v1/users/me/events` | — | SSE `text/event-stream` | authenticated | User push events (§4.3) |

```python
class UpdateProfile(BaseModel):
    """Fields a user can update on their own profile."""
    given_name: str | None = None
    family_name: str | None = None
    job_role: str | None = None
    notification_preferences: dict | None = None
```

### 3.4 Roles — WP1

| Method | Path | Request | Response | Permission | Notes |
|---|---|---|---|---|---|
| `GET` | `/api/v1/roles` | — | `list[RoleResponse]` | `list_user_roles` | |
| `POST` | `/api/v1/roles` | `CreateRole` | `RoleResponse` | `list_user_roles` | Spec §2.4 groups create/update under role management |
| `GET` | `/api/v1/roles/{id}` | — | `RoleResponse` | `list_user_roles` | |
| `PATCH` | `/api/v1/roles/{id}` | `UpdateRole` | `RoleResponse` | `list_user_roles` | Spec §2.4 groups create/update under role management |
| `DELETE` | `/api/v1/roles/{id}` | — | `204 No Content` | `delete_user_roles` | |
| `PUT` | `/api/v1/users/{id}/roles` | `{ role_ids: list[UUID] }` | `UserResponse` | `update_user_role` | Replace user's roles |
| `GET` | `/api/v1/permissions` | — | `list[PermissionResponse]` | `list_user_roles` | All available permissions |

```python
class UpdateRole(BaseModel):
    name: str | None = None
    description: str | None = None
    permission_ids: list[UUID] | None = None
```

### 3.5 Knowledge Bases — WP3

| Method | Path | Request | Response | Permission | Notes |
|---|---|---|---|---|---|
| `GET` | `/api/v1/knowledge-bases` | — | `list[KnowledgeBaseResponse]` | authenticated | |
| `POST` | `/api/v1/knowledge-bases` | `CreateKnowledgeBase` | `KnowledgeBaseResponse` | `create_knowledge_base` | |
| `GET` | `/api/v1/knowledge-bases/{id}` | — | `KnowledgeBaseResponse` | authenticated | |
| `PATCH` | `/api/v1/knowledge-bases/{id}` | `UpdateKnowledgeBase` | `KnowledgeBaseResponse` | `create_knowledge_base` | Update name |
| `DELETE` | `/api/v1/knowledge-bases/{id}` | — | `204 No Content` | `delete_knowledge_base` | Cascades to documents |
| `POST` | `/api/v1/knowledge-bases/{id}/sync` | — | `202 Accepted` | `sync_knowledge_base` | Enqueues Celery task |

```python
class UpdateKnowledgeBase(BaseModel):
    name: str | None = None
```

### 3.6 Documents — WP3

| Method | Path | Request | Response | Permission | Notes |
|---|---|---|---|---|---|
| `POST` | `/api/v1/knowledge-bases/{kb_id}/documents` | `multipart/form-data` | `DocumentResponse` | `upload_documents` | Max 50MB |
| `GET` | `/api/v1/knowledge-bases/{kb_id}/documents` | `DocumentFilters` (query) | `Page[DocumentResponse]` | authenticated | |
| `GET` | `/api/v1/documents/{id}` | — | `DocumentResponse` | authenticated | |
| `DELETE` | `/api/v1/documents/{id}` | — | `204 No Content` | `delete_documents` | DB + Qdrant cleanup |
| `GET` | `/api/v1/documents/{id}/versions` | — | `list[DocumentVersion]` | authenticated | |
| `POST` | `/api/v1/documents/{id}/retry` | — | `DocumentResponse` | `upload_documents` | Retry failed/DLQ |

### 3.7 Search — WP3

| Method | Path | Request | Response | Permission | Notes |
|---|---|---|---|---|---|
| `POST` | `/api/v1/search` | `SearchRequest` | `list[SearchResult]` | authenticated | Hybrid search pipeline |

### 3.8 Conversations — WP5

| Method | Path | Request | Response | Permission | Notes |
|---|---|---|---|---|---|
| `GET` | `/api/v1/conversations` | `?page=1&page_size=50` | `Page[ConversationResponse]` | authenticated | User's own conversations |
| `POST` | `/api/v1/conversations` | `CreateConversation` | `ConversationResponse` | authenticated | |
| `GET` | `/api/v1/conversations/{id}` | — | `ConversationResponse` | authenticated | Must be owner |
| `PATCH` | `/api/v1/conversations/{id}` | `UpdateConversation` | `ConversationResponse` | authenticated | Rename |
| `DELETE` | `/api/v1/conversations/{id}` | — | `204 No Content` | authenticated | Soft delete |
| `GET` | `/api/v1/conversations/{id}/messages` | `?page=1&page_size=50` | `Page[MessageResponse]` | authenticated | Chronological order |
| `POST` | `/api/v1/conversations/{id}/messages` | `SendMessage` | `MessageResponse` | authenticated | User message; triggers agent |
| `POST` | `/api/v1/conversations/{id}/cancel` | — | `204 No Content` | authenticated | Cancel in-flight generation |
| `GET` | `/api/v1/conversations/{id}/stream` | — | SSE `text/event-stream` | authenticated | See §4 for event types |
| `GET` | `/api/v1/conversations/{id}/export` | `?format=pdf\|markdown` | `application/pdf` or `text/markdown` | authenticated | Branded PDF or Markdown |

### 3.9 Personas — WP5

| Method | Path | Request | Response | Permission | Notes |
|---|---|---|---|---|---|
| `GET` | `/api/v1/personas` | — | `list[PersonaResponse]` | authenticated | |
| `POST` | `/api/v1/personas` | `CreatePersona` | `PersonaResponse` | `create_persona` | |
| `GET` | `/api/v1/personas/{id}` | — | `PersonaResponse` | authenticated | |
| `PATCH` | `/api/v1/personas/{id}` | `UpdatePersona` | `PersonaResponse` | `update_persona` | |
| `DELETE` | `/api/v1/personas/{id}` | — | `204 No Content` | `delete_persona` | |
| `POST` | `/api/v1/personas/{id}/duplicate` | — | `PersonaResponse` | `create_persona` | Clone as template |

### 3.10 Guardrails — WP1

| Method | Path | Request | Response | Permission | Notes |
|---|---|---|---|---|---|
| `GET` | `/api/v1/guardrails` | — | `list[GuardrailResponse]` | `list_guardrails` | |
| `POST` | `/api/v1/guardrails` | `CreateGuardrail` | `GuardrailResponse` | `create_guardrail` | |
| `GET` | `/api/v1/guardrails/{id}` | — | `GuardrailResponse` | `view_guardrail` | |
| `PATCH` | `/api/v1/guardrails/{id}` | `UpdateGuardrail` | `GuardrailResponse` | `update_guardrail` | |
| `DELETE` | `/api/v1/guardrails/{id}` | — | `204 No Content` | `delete_guardrail` | |

```python
class GuardrailResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    description: str | None
    status: GuardrailStatus
    configuration_rules: dict
    created_at: datetime
    updated_at: datetime

class CreateGuardrail(BaseModel):
    name: str
    description: str | None = None
    configuration_rules: dict | None = None

class UpdateGuardrail(BaseModel):
    name: str | None = None
    description: str | None = None
    configuration_rules: dict | None = None
```

### 3.11 Conversation Templates — WP5

| Method | Path | Request | Response | Permission | Notes |
|---|---|---|---|---|---|
| `GET` | `/api/v1/conversation-templates` | `?category=&industry_vertical=` | `list[ConversationTemplateResponse]` | authenticated | |

```python
class ConversationTemplateResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    prompt_text: str
    category: str | None
    industry_vertical: str | None
    created_at: datetime
```

### 3.12 Policy Definitions — WP6

| Method | Path | Request | Response | Permission | Notes |
|---|---|---|---|---|---|
| `GET` | `/api/v1/policy-definitions` | `?group_id=&status=` | `list[PolicyDefinitionResponse]` | authenticated | |
| `POST` | `/api/v1/policy-definitions` | `CreatePolicyDefinition` | `PolicyDefinitionResponse` | `manage_policy_review_schedule` | |
| `GET` | `/api/v1/policy-definitions/{id}` | — | `PolicyDefinitionResponse` | authenticated | |
| `PATCH` | `/api/v1/policy-definitions/{id}` | `UpdatePolicyDefinition` | `PolicyDefinitionResponse` | `manage_policy_review_schedule` | |
| `DELETE` | `/api/v1/policy-definitions/{id}` | — | `204 No Content` | `manage_policy_review_schedule` | |
| `GET` | `/api/v1/policy-definition-groups` | — | `list[PolicyDefinitionGroupResponse]` | authenticated | |
| `POST` | `/api/v1/policy-definition-groups` | `CreatePolicyDefinitionGroup` | `PolicyDefinitionGroupResponse` | `manage_policy_review_schedule` | |
| `PATCH` | `/api/v1/policy-definition-groups/{id}` | `UpdatePolicyDefinitionGroup` | `PolicyDefinitionGroupResponse` | `manage_policy_review_schedule` | |
| `DELETE` | `/api/v1/policy-definition-groups/{id}` | — | `204 No Content` | `manage_policy_review_schedule` | SET NULL on definitions |
| `GET` | `/api/v1/policy-definition-topics` | — | `list[PolicyDefinitionTopicResponse]` | authenticated | |
| `POST` | `/api/v1/policy-definition-topics` | `CreatePolicyDefinitionTopic` | `PolicyDefinitionTopicResponse` | `manage_policy_review_schedule` | |
| `PATCH` | `/api/v1/policy-definition-topics/{id}` | `UpdatePolicyDefinitionTopic` | `PolicyDefinitionTopicResponse` | `manage_policy_review_schedule` | |
| `DELETE` | `/api/v1/policy-definition-topics/{id}` | — | `204 No Content` | `manage_policy_review_schedule` | Cascade removes links |

```python
class PolicyDefinitionResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    uri: str
    status: str   # "active" | "inactive"
    group_id: UUID | None
    group: "PolicyDefinitionGroupResponse | None"
    description: str | None
    is_required: bool
    review_cycle: ReviewCycle | None
    name_variants: list[str]
    scoring_criteria: dict
    compliance_criteria: dict
    required_sections: list[str]
    legislation_references: list[dict]
    last_regulatory_update_date: datetime | None
    regulatory_change_flags: list[dict]
    topics: list["PolicyDefinitionTopicResponse"]
    created_at: datetime
    updated_at: datetime

class PolicyDefinitionGroupResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    description: str | None
    created_at: datetime

class PolicyDefinitionTopicResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    created_at: datetime

class CreatePolicyDefinition(BaseModel):
    name: str
    uri: str
    status: str = "active"
    group_id: UUID | None = None
    description: str | None = None
    is_required: bool = False
    review_cycle: ReviewCycle | None = None
    name_variants: list[str] | None = None
    scoring_criteria: dict | None = None
    compliance_criteria: dict | None = None
    required_sections: list[str] | None = None
    legislation_references: list[dict] | None = None
    topic_ids: list[UUID] | None = None

class UpdatePolicyDefinition(BaseModel):
    name: str | None = None
    status: str | None = None
    group_id: UUID | None = None
    description: str | None = None
    is_required: bool | None = None
    review_cycle: ReviewCycle | None = None
    name_variants: list[str] | None = None
    scoring_criteria: dict | None = None
    compliance_criteria: dict | None = None
    required_sections: list[str] | None = None
    legislation_references: list[dict] | None = None
    topic_ids: list[UUID] | None = None

class CreatePolicyDefinitionGroup(BaseModel):
    name: str
    description: str | None = None

class UpdatePolicyDefinitionGroup(BaseModel):
    name: str | None = None
    description: str | None = None

class CreatePolicyDefinitionTopic(BaseModel):
    name: str

class UpdatePolicyDefinitionTopic(BaseModel):
    name: str | None = None
```

### 3.13 Policy Reviews — WP5/WP6

| Method | Path | Request | Response | Permission | Notes |
|---|---|---|---|---|---|
| `POST` | `/api/v1/policy-reviews` | `multipart/form-data` + optional `policy_definition_id` | `PolicyReviewResponse` | authenticated | Uploads policy doc |
| `GET` | `/api/v1/policy-reviews` | `PolicyReviewFilters` (query) | `Page[PolicyReviewResponse]` | authenticated | |
| `GET` | `/api/v1/policy-reviews/{id}` | — | `PolicyReviewResponse` | authenticated | |
| `POST` | `/api/v1/policy-reviews/{id}/cancel` | — | `PolicyReviewResponse` | authenticated | |
| `GET` | `/api/v1/policy-reviews/{id}/stream` | — | SSE `text/event-stream` | authenticated | See §4.2 |
| `GET` | `/api/v1/policy-reviews/{id}/export` | `?format=pdf` | `application/pdf` | authenticated | Branded PDF |

### 3.14 Regulatory Change Alerts

| Method | Path | Request | Response | Permission | Notes |
|---|---|---|---|---|---|
| `GET` | `/api/v1/regulatory-alerts` | `?status=pending` | `Page[RegulatoryAlertResponse]` | `view_regulatory_alerts` | |
| `GET` | `/api/v1/regulatory-alerts/{id}` | — | `RegulatoryAlertResponse` | `view_regulatory_alerts` | |
| `PATCH` | `/api/v1/regulatory-alerts/{id}` | `UpdateAlert` | `RegulatoryAlertResponse` | `view_regulatory_alerts` | Acknowledge/dismiss/action |

```python
class RegulatoryAlertResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    change_type: RegulatoryChangeType
    source_reference: str | None
    summary: str | None
    affected_policy_definition_ids: list[UUID]
    status: AlertStatus
    detected_at: datetime
    acknowledged_at: datetime | None
    actioned_at: datetime | None
    created_at: datetime

class UpdateAlert(BaseModel):
    status: AlertStatus
```

### 3.15 Activity Logs — WP1

| Method | Path | Request | Response | Permission | Notes |
|---|---|---|---|---|---|
| `GET` | `/api/v1/activity-logs` | `ActivityLogFilters` (query) | `Page[ActivityLogResponse]` | `list_activity_logs` | |
| `GET` | `/api/v1/activity-logs/export` | `ActivityLogFilters` (query) | `text/csv` | `export_activity_logs` | CSV download |

```python
class ActivityLogFilters(BaseModel):
    tags: list[ActivityLogTag] | None = None
    user_id: UUID | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    search: str | None = None
    page: int = 1
    page_size: int = 50

class ActivityLogResponse(BaseModel):
    id: UUID
    timestamp: datetime
    user_id: UUID | None
    user_name: str | None  # Denormalised for display
    action: str
    detail: str | None
    tags: list[ActivityLogTag]
    created_at: datetime
```

### 3.16 Billing & Usage

| Method | Path | Request | Response | Permission | Notes |
|---|---|---|---|---|---|
| `GET` | `/api/v1/usage/summary` | `?date_from=&date_to=` | `UsageSummary` | `query_account_usage_stats` | |
| `GET` | `/api/v1/usage/events` | `?page=1&page_size=50&date_from=&date_to=` | `Page[BillingEventResponse]` | `query_account_usage_stats` | |

```python
class UsageSummary(BaseModel):
    credit_limit: float
    credits_used: float
    credits_remaining: float
    billing_period_start: datetime | None
    billing_period_end: datetime | None
    breakdown_by_feature: dict[BillingFeature, float]
    breakdown_by_model: dict[str, float]

class BillingEventResponse(BaseModel):
    id: UUID
    event_type: BillingEventType
    amount: float
    agent_invocation_id: UUID | None
    model_id: str | None
    feature: BillingFeature | None
    description: str | None
    created_at: datetime
```

### 3.17 News Feed

| Method | Path | Request | Response | Permission | Notes |
|---|---|---|---|---|---|
| `GET` | `/api/v1/news` | `?page=1&page_size=20` | `Page[NewsStoryResponse]` | authenticated | Newest first |
| `POST` | `/api/v1/news/refresh` | — | `202 Accepted` | authenticated | Enqueues feed fetch |

```python
class NewsStoryResponse(BaseModel):
    id: UUID
    title: str
    url: str
    snippet: str | None
    source: str | None
    image_url: str | None
    published_at: datetime | None
    fetched_at: datetime
```

### 3.18 Canvas

| Method | Path | Request | Response | Permission | Notes |
|---|---|---|---|---|---|
| `POST` | `/api/v1/canvases` | `CreateCanvas` | `CanvasResponse` | authenticated | |
| `GET` | `/api/v1/canvases/{id}` | — | `CanvasResponse` | authenticated | Must be owner |
| `PATCH` | `/api/v1/canvases/{id}` | `UpdateCanvas` | `CanvasResponse` | authenticated | Auto-save target |
| `GET` | `/api/v1/canvases/{id}/export` | `?format=pdf\|markdown` | `application/pdf` or `text/markdown` | authenticated | Branded PDF or Markdown |

```python
class CanvasResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    user_id: UUID
    title: str | None
    content: str | None
    html_content: str | None
    save_state: str | None
    created_at: datetime
    updated_at: datetime

class CreateCanvas(BaseModel):
    title: str | None = None
    content: str | None = None
    html_content: str | None = None

class UpdateCanvas(BaseModel):
    title: str | None = None
    content: str | None = None
    html_content: str | None = None
    save_state: str | None = None
```

### 3.19 Feedback

| Method | Path | Request | Response | Permission | Notes |
|---|---|---|---|---|---|
| `POST` | `/api/v1/messages/{id}/feedback` | `CreateFeedback` | `FeedbackResponse` | authenticated | Upsert per user per message |

### 3.20 Analytics Dashboard — WP1/shared

| Method | Path | Request | Response | Permission | Notes |
|---|---|---|---|---|---|
| `GET` | `/api/v1/analytics/summary` | `?date_from=&date_to=` | `AnalyticsSummary` | `show_dashboard` | |
| `GET` | `/api/v1/analytics/time-series` | `?metric=&date_from=&date_to=&interval=day` | `TimeSeriesResponse` | `show_dashboard` | |

```python
class AnalyticsSummary(BaseModel):
    credit_usage: UsageSummary
    conversations_started: int
    users_created: int
    policy_reviews_completed: int
    average_confidence: dict[ConfidenceLevel, int]  # Count per level
    feedback_positive: int
    feedback_negative: int

class TimeSeriesPoint(BaseModel):
    timestamp: datetime
    value: float

class TimeSeriesResponse(BaseModel):
    metric: str
    interval: str
    data: list[TimeSeriesPoint]
```

### 3.21 Reports

| Method | Path | Request | Response | Permission | Notes |
|---|---|---|---|---|---|
| `POST` | `/api/v1/reports/compliance` | `{ date_from: str, date_to: str }` | `202 Accepted` | `export_compliance_reports` | Enqueues Celery task |

### 3.22 Health Check — public

| Method | Path | Request | Response | Permission | Notes |
|---|---|---|---|---|---|
| `GET` | `/api/v1/health` | — | `HealthResponse` | public | Readiness probe |

```python
class HealthResponse(BaseModel):
    status: str          # "healthy" | "degraded" | "unhealthy"
    database: str        # "connected" | "error"
    qdrant: str          # "connected" | "error"
    redis: str           # "connected" | "error"
    lex: str             # "connected" | "fallback" | "error"
    version: str         # Application version
```

---

## 4. SSE Event Definitions

### 4.1 Conversation Stream Events

**Endpoint**: `GET /api/v1/conversations/{id}/stream`
**Content-Type**: `text/event-stream`
**Auth**: Bearer JWT required

Each event is sent as:
```
event: <event_type>
data: <JSON payload>

```

#### Event Type Reference (Spec §3.1.10)

```python
# agents/streaming.py
from pydantic import BaseModel
from typing import Literal

# -- Agent lifecycle events --

class AgentStartEvent(BaseModel):
    """Sub-agent has begun processing."""
    event_type: Literal["agent_start"] = "agent_start"
    agent_name: str           # "router", "orchestrator", "legislation_worker", etc.
    task_description: str     # "Searching UK housing legislation..."

class AgentProgressEvent(BaseModel):
    """Sub-agent progress update (thinking/searching)."""
    event_type: Literal["agent_progress"] = "agent_progress"
    agent_name: str
    status_text: str          # "Found 3 relevant Acts, analysing sections..."

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
    citation: str             # Neutral citation, e.g. "[2023] UKSC 42"
    court: str
    date: str                 # ISO date string

class AnnotationEvent(BaseModel):
    """Expert commentary/annotation discovered on a cited source."""
    event_type: Literal["annotation"] = "annotation"
    content: str
    contributor: str
    type: str                 # "expert_commentary", etc.

class CompanyPolicySourceEvent(BaseModel):
    """Internal policy document reference discovered."""
    event_type: Literal["company_policy_source"] = "company_policy_source"
    document_name: str
    section: str

class ParliamentarySourceEvent(BaseModel):
    """Parliamentary data reference discovered (Hansard, Written Questions, etc.)."""
    event_type: Literal["parliamentary_source"] = "parliamentary_source"
    type: str                 # "debate", "written_question", "committee"
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
    message_id: str           # UUID as string
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

# -- Union type for parsing --
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
)
```

### 4.2 Policy Review Stream Events

**Endpoint**: `GET /api/v1/policy-reviews/{id}/stream`

Uses the same `StreamEvent` union type above plus:

```python
class PolicyReviewStatusEvent(BaseModel):
    """Policy review progress update."""
    event_type: Literal["policy_review_status"] = "policy_review_status"
    state: PolicyReviewState
    status_text: str          # "Analysing policy structure..."

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
```

### 4.3 User-Level Push Events

**Endpoint**: `GET /api/v1/users/me/events`

Server-pushed notifications for the current user:

```python
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
    percentage_used: float    # 70, 85, 95, 100
    credits_remaining: float
```

---

## 5. Celery Task Signatures

All tenant-scoped tasks receive `tenant_id` as a required parameter.
All tasks use structured logging with `tenant_id` and `request_id` where applicable.
Platform-wide tasks (`check_lex_health`, `cleanup_expired_activity_logs`) are
exceptions — they operate across all tenants or on shared infrastructure.

### 5.1 Document Processing Pipeline — WP3

**Queue**: `knowledge_ingest`

```python
# knowledge/tasks.py

@celery_app.task(
    name="knowledge.process_document",
    queue="knowledge_ingest",
    bind=True,
    max_retries=3,
    default_retry_delay=1,      # Exponential: 1s, 2s, 4s
)
def process_document(
    self,
    document_id: str,           # UUID as string (Celery serialisation)
    tenant_id: str,
) -> None:
    """Full pipeline: validate → extract → chunk → contextualise → embed → index.
    Updates document.processing_state at each step.
    On failure after max retries, sets dead_letter=True."""
    ...

@celery_app.task(
    name="knowledge.validate_document",
    queue="knowledge_ingest",
)
def validate_document(document_id: str, tenant_id: str) -> None:
    """Check file format, size, virus scan placeholder.
    Transitions: uploaded → validating → extracting_text | failed."""
    ...

@celery_app.task(
    name="knowledge.extract_text",
    queue="knowledge_ingest",
)
def extract_text(document_id: str, tenant_id: str) -> None:
    """PDF/DOCX/TXT text extraction.
    Transitions: extracting_text → chunking | failed."""
    ...

@celery_app.task(
    name="knowledge.chunk_document",
    queue="knowledge_ingest",
)
def chunk_document(document_id: str, tenant_id: str) -> None:
    """Structure-aware or fixed-size chunking.
    Creates document_chunks rows.
    Transitions: chunking → contextualising | failed."""
    ...

@celery_app.task(
    name="knowledge.contextualise_chunks",
    queue="knowledge_ingest",
)
def contextualise_chunks(document_id: str, tenant_id: str) -> None:
    """Call Anthropic Haiku to generate contextual prefix for each chunk.
    Transitions: contextualising → embedding | failed."""
    ...

@celery_app.task(
    name="knowledge.embed_chunks",
    queue="knowledge_ingest",
)
def embed_chunks(document_id: str, tenant_id: str) -> None:
    """Generate vector embeddings for all chunks (batched).
    Transitions: embedding → indexing | failed."""
    ...

@celery_app.task(
    name="knowledge.index_document",
    queue="knowledge_ingest",
)
def index_document(document_id: str, tenant_id: str) -> None:
    """Upsert vectors + BM25 payload into Qdrant collection
    tenant_{tenant_id}_documents.
    Transitions: indexing → ready | failed."""
    ...

@celery_app.task(
    name="knowledge.delete_document_vectors",
    queue="knowledge_ingest",
)
def delete_document_vectors(document_id: str, tenant_id: str) -> None:
    """Remove all vectors for a document from Qdrant."""
    ...

@celery_app.task(
    name="knowledge.sync_knowledge_base",
    queue="knowledge_ingest",
)
def sync_knowledge_base(knowledge_base_id: str, tenant_id: str) -> None:
    """Sync a catalog-type knowledge base from its configured source."""
    ...
```

### 5.2 AI Engine Tasks — WP5

**Queue**: `interaction`

```python
# agents/tasks.py

@celery_app.task(
    name="agents.generate_title",
    queue="interaction",
)
def generate_title(conversation_id: str, tenant_id: str) -> None:
    """Generate conversation title from first user message using Haiku.
    Updates conversation.title. Emits SSE title events."""
    ...

@celery_app.task(
    name="agents.run_policy_review",
    queue="interaction",
    soft_time_limit=300,        # 5 minute soft limit
    time_limit=360,             # 6 minute hard limit
)
def run_policy_review(
    review_id: str,
    tenant_id: str,
    user_id: str,
) -> None:
    """Execute full policy review pipeline:
    identify policy type → evaluate against ontology → verify citations.
    Streams progress via SSE. Updates policy_reviews.state and .result."""
    ...
```

### 5.3 Verification Tasks — WP5

**Queue**: `verification`

```python
# agents/tasks.py

@celery_app.task(
    name="agents.verify_citations",
    queue="verification",
)
def verify_citations(
    invocation_id: str,
    tenant_id: str,
    citations: list[dict],
) -> dict:
    """Verify each citation against Lex API.
    Returns: { citations_checked, citations_verified, issues, results }.
    Called by the orchestrator after response generation."""
    ...
```

### 5.4 Monitoring Tasks — Scheduled

**Queue**: `monitoring`

```python
# monitoring/tasks.py

@celery_app.task(
    name="monitoring.check_regulatory_changes",
    queue="monitoring",
)
def check_regulatory_changes(tenant_id: str) -> None:
    """Compare current Lex dataset against last known state.
    Creates regulatory_change_alerts for any detected changes.
    Matches changes to affected policy definitions by legislation references.
    Runs weekly per tenant (Celery Beat schedule)."""
    ...

@celery_app.task(
    name="monitoring.refresh_news_feed",
    queue="monitoring",
)
def refresh_news_feed(tenant_id: str) -> None:
    """Fetch RSS/Atom feeds from tenant's configured news_feed_urls.
    Upsert news_stories. Deduplicate by URL."""
    ...

@celery_app.task(
    name="monitoring.check_lex_health",
    queue="monitoring",
)
def check_lex_health() -> None:
    """Health check self-hosted Lex every 30 seconds.
    After 3 consecutive failures, enable fallback to public API.
    Not tenant-scoped."""
    ...
```

### 5.5 Reporting Tasks — Scheduled

**Queue**: `reporting`

```python
# reporting/tasks.py

@celery_app.task(
    name="reporting.generate_compliance_report",
    queue="reporting",
)
def generate_compliance_report(tenant_id: str, date_range: dict) -> str:
    """Generate aggregate compliance report PDF.
    Returns the file path / storage key for the generated report."""
    ...

@celery_app.task(
    name="reporting.cleanup_expired_activity_logs",
    queue="reporting",
)
def cleanup_expired_activity_logs() -> int:
    """Delete activity_logs where retention_expiry_at < now().
    Returns count of deleted rows. Runs daily via Celery Beat.
    Not tenant-scoped (processes all tenants)."""
    ...

@celery_app.task(
    name="reporting.process_data_erasure",
    queue="reporting",
)
def process_data_erasure(user_id: str, tenant_id: str) -> None:
    """Hard delete all data for a soft-deleted user:
    conversations, messages, canvases, feedback, activity log entries.
    Triggered when user.deleted_at is set. Runs after a grace period."""
    ...
```

### 5.6 Celery Beat Schedule

```python
# celeryconfig.py
from celery.schedules import crontab

beat_schedule = {
    "check-lex-health": {
        "task": "monitoring.check_lex_health",
        "schedule": 30.0,                        # Every 30 seconds
    },
    "refresh-news-feeds": {
        "task": "monitoring.refresh_news_feed",
        "schedule": crontab(minute="*/30"),       # Every 30 minutes per tenant
        # Dispatched per-tenant by a fan-out wrapper
    },
    "check-regulatory-changes": {
        "task": "monitoring.check_regulatory_changes",
        "schedule": crontab(day_of_week="sunday", hour=2, minute=0),  # Weekly
        # Dispatched per-tenant by a fan-out wrapper
    },
    "cleanup-expired-logs": {
        "task": "reporting.cleanup_expired_activity_logs",
        "schedule": crontab(hour=3, minute=0),    # Daily at 03:00
    },
    "process-pending-document": {
        "task": "knowledge.process_document",
        "schedule": 15.0,                         # Every 15 seconds (polls for pending)
        # Fan-out: picks up all documents with state=uploaded
    },
}
```

---

## 6. TypeScript Type Definitions

These types are consumed by the Next.js frontend (`frontend/src/lib/types/`).
They MUST be kept in sync with the Pydantic models above.

### 6.1 Enums

```typescript
// lib/types/enums.ts

export type SubscriptionTier = "starter" | "professional" | "enterprise";
export type UserStatus = "pending" | "active" | "disabled" | "deleted";
export type ConversationState = "pending" | "waiting_for_reply" | "generating_reply" | "outputting_reply" | "ready";
export type MessageRole = "user" | "assistant";
export type MessageState = "pending" | "success" | "error" | "cancelled";
export type ConfidenceLevel = "high" | "medium" | "low";
export type VerificationStatus = "verified" | "unverified" | "removed" | "pre_1963_digitised";
export type AgentInvocationMode = "conversation" | "policy_review";
export type ModelTier = "haiku" | "sonnet" | "opus";
export type KnowledgeBaseCategory = "legislation" | "case_law" | "explanatory_notes" | "amendments" | "company_policy" | "sector_knowledge" | "parliamentary";
export type KnowledgeBaseSourceType = "lex_api" | "uploaded" | "catalog" | "parliament_mcp";
export type DocumentProcessingState = "uploaded" | "validating" | "extracting_text" | "chunking" | "contextualising" | "embedding" | "indexing" | "ready" | "failed";
export type GuardrailStatus = "creating" | "updating" | "versioning" | "ready" | "failed" | "deleting";
export type ReviewCycle = "annual" | "monthly" | "quarterly";
export type PolicyReviewState = "pending" | "processing" | "verifying" | "complete" | "error" | "cancelled";
export type RAGRating = "green" | "amber" | "red";
export type RegulatoryChangeType = "new_legislation" | "amendment" | "new_regulatory_standard" | "consultation";
export type AlertStatus = "pending" | "acknowledged" | "dismissed" | "actioned";
export type BillingEventType = "credit" | "usage" | "adjustment";
export type BillingFeature = "conversation" | "policy_review" | "title_generation" | "regulatory_monitoring";
export type ActivityLogTag = "user" | "system" | "security" | "ai";
export type FeedbackRating = "up" | "down";
export type FeedbackReviewStatus = "pending" | "reviewed" | "actioned";
```

### 6.2 Shared Types

```typescript
// lib/types/common.ts

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  has_next: boolean;
}

export interface ErrorResponse {
  code: string;
  message: string;
  detail?: Record<string, unknown>;
}
```

### 6.3 Tenant & Auth

```typescript
// lib/types/tenant.ts

export interface BrandingConfig {
  logo_url: string | null;
  favicon_url: string | null;
  app_name: string | null;
  primary_colour: string | null;
  secondary_colour: string | null;
  custom_domain: string | null;
  disclaimer_text: string | null;
}

export interface AIConfig {
  confidence_thresholds: Record<string, unknown> | null;
  topic_restrictions: string[] | null;
  model_overrides: Record<string, unknown> | null;
}

export interface TenantConfig {
  id: string;
  name: string;
  slug: string;
  industry_vertical: string | null;
  branding: BrandingConfig;
  ai_config: AIConfig;
  subscription_tier: SubscriptionTier;
  credit_limit: number;
  billing_period_start: string | null;
  billing_period_end: string | null;
  is_active: boolean;
  news_feed_urls: string[];
  external_source_integrations: Record<string, unknown>[];
  vector_namespace: string | null;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  expires_in: number;
}
```

### 6.4 Users & Roles

```typescript
// lib/types/users.ts

export interface UserResponse {
  id: string;
  tenant_id: string;
  email: string;
  given_name: string;
  family_name: string;
  job_role: string | null;
  status: UserStatus;
  last_active_at: string | null;
  notification_preferences: Record<string, unknown>;
  roles: RoleResponse[];
  created_at: string;
  updated_at: string;
}

export interface RoleResponse {
  id: string;
  tenant_id: string;
  name: string;
  description: string | null;
  permissions: PermissionResponse[];
  created_at: string;
}

export interface PermissionResponse {
  id: string;
  name: string;
  description: string | null;
}

export interface BulkInviteResult {
  created: number;
  skipped: number;
  errors: Record<string, unknown>[];
}
```

### 6.5 Conversations & Messages

```typescript
// lib/types/conversations.ts

export interface ConversationResponse {
  id: string;
  tenant_id: string;
  user_id: string;
  title: string | null;
  state: ConversationState;
  template_id: string | null;
  message_count: number;
  created_at: string;
  updated_at: string;
}

export interface MessageResponse {
  id: string;
  conversation_id: string;
  request_id: string | null;
  role: MessageRole;
  content: string;
  state: MessageState;
  metadata: Record<string, unknown>;
  file_attachments: Record<string, unknown>[];
  confidence_level: ConfidenceLevel | null;
  verification_result: Record<string, unknown> | null;
  feedback: FeedbackResponse | null;
  created_at: string;
}

export interface ConversationTemplateResponse {
  id: string;
  tenant_id: string;
  name: string;
  prompt_text: string;
  category: string | null;
  industry_vertical: string | null;
  created_at: string;
}

export interface FeedbackResponse {
  id: string;
  message_id: string;
  user_id: string;
  rating: FeedbackRating;
  comment: string | null;
  review_status: FeedbackReviewStatus;
  created_at: string;
}
```

### 6.6 Knowledge Base & Documents

```typescript
// lib/types/knowledge.ts

export interface KnowledgeBaseResponse {
  id: string;
  tenant_id: string;
  name: string;
  category: KnowledgeBaseCategory;
  source_type: KnowledgeBaseSourceType;
  document_count: number;
  ready_document_count: number;
  created_at: string;
  updated_at: string;
}

export interface DocumentResponse {
  id: string;
  tenant_id: string;
  knowledge_base_id: string;
  name: string;
  document_uri: string;
  source_uri: string | null;
  mime_type: string | null;
  byte_size: number | null;
  hash: string | null;
  processing_state: DocumentProcessingState;
  version_number: number;
  previous_version_id: string | null;
  metadata: Record<string, unknown>;
  chunk_count: number;
  retry_count: number;
  last_error_message: string | null;
  dead_letter: boolean;
  created_at: string;
  updated_at: string;
}

export interface DocumentVersion {
  id: string;
  name: string;
  version_number: number;
  processing_state: DocumentProcessingState;
  byte_size: number | null;
  created_at: string;
}

export interface SearchResult {
  chunk_id: string;
  document_id: string;
  document_name: string;
  document_uri: string;
  knowledge_base_category: KnowledgeBaseCategory;
  chunk_index: number;
  content: string;
  contextual_prefix: string | null;
  score: number;
  source_uri: string | null;
  metadata: Record<string, unknown>;
}
```

### 6.7 Personas & Guardrails

```typescript
// lib/types/personas.ts

export interface PersonaResponse {
  id: string;
  tenant_id: string;
  name: string;
  description: string | null;
  system_instructions: string | null;
  activated_skills: Record<string, unknown>[];
  usage_count: number;
  created_at: string;
  updated_at: string;
}

// lib/types/guardrails.ts

export interface GuardrailResponse {
  id: string;
  tenant_id: string;
  name: string;
  description: string | null;
  status: GuardrailStatus;
  configuration_rules: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}
```

### 6.8 Policy Definitions & Reviews

```typescript
// lib/types/policy.ts

export interface PolicyDefinitionResponse {
  id: string;
  tenant_id: string;
  name: string;
  uri: string;
  status: "active" | "inactive";
  group_id: string | null;
  group: PolicyDefinitionGroupResponse | null;
  description: string | null;
  is_required: boolean;
  review_cycle: ReviewCycle | null;
  name_variants: string[];
  scoring_criteria: Record<string, unknown>;
  compliance_criteria: Record<string, unknown>;
  required_sections: string[];
  legislation_references: Record<string, unknown>[];
  last_regulatory_update_date: string | null;
  regulatory_change_flags: Record<string, unknown>[];
  topics: PolicyDefinitionTopicResponse[];
  created_at: string;
  updated_at: string;
}

export interface PolicyDefinitionGroupResponse {
  id: string;
  tenant_id: string;
  name: string;
  description: string | null;
  created_at: string;
}

export interface PolicyDefinitionTopicResponse {
  id: string;
  tenant_id: string;
  name: string;
  created_at: string;
}

export interface PolicyReviewResponse {
  id: string;
  tenant_id: string;
  request_id: string | null;
  user_id: string;
  policy_definition_id: string | null;
  state: PolicyReviewState;
  result: Record<string, unknown> | null;
  source: string | null;
  citation_verification_result: Record<string, unknown> | null;
  version: number;
  created_at: string;
  updated_at: string;
}
```

### 6.9 Regulatory Alerts & Activity

```typescript
// lib/types/regulatory.ts

export interface RegulatoryAlertResponse {
  id: string;
  tenant_id: string;
  change_type: RegulatoryChangeType;
  source_reference: string | null;
  summary: string | null;
  affected_policy_definition_ids: string[];
  status: AlertStatus;
  detected_at: string;
  acknowledged_at: string | null;
  actioned_at: string | null;
  created_at: string;
}

// lib/types/activity.ts

export interface ActivityLogResponse {
  id: string;
  timestamp: string;
  user_id: string | null;
  user_name: string | null;
  action: string;
  detail: string | null;
  tags: ActivityLogTag[];
  created_at: string;
}
```

### 6.10 Billing & Analytics

```typescript
// lib/types/billing.ts

export interface UsageSummary {
  credit_limit: number;
  credits_used: number;
  credits_remaining: number;
  billing_period_start: string | null;
  billing_period_end: string | null;
  breakdown_by_feature: Partial<Record<BillingFeature, number>>;
  breakdown_by_model: Record<string, number>;
}

export interface BillingEventResponse {
  id: string;
  event_type: BillingEventType;
  amount: number;
  agent_invocation_id: string | null;
  model_id: string | null;
  feature: BillingFeature | null;
  description: string | null;
  created_at: string;
}

// lib/types/analytics.ts

export interface AnalyticsSummary {
  credit_usage: UsageSummary;
  conversations_started: number;
  users_created: number;
  policy_reviews_completed: number;
  average_confidence: Partial<Record<ConfidenceLevel, number>>;
  feedback_positive: number;
  feedback_negative: number;
}

export interface TimeSeriesPoint {
  timestamp: string;
  value: number;
}

export interface TimeSeriesResponse {
  metric: string;
  interval: string;
  data: TimeSeriesPoint[];
}
```

### 6.11 News & Canvas

```typescript
// lib/types/news.ts

export interface NewsStoryResponse {
  id: string;
  title: string;
  url: string;
  snippet: string | null;
  source: string | null;
  image_url: string | null;
  published_at: string | null;
  fetched_at: string;
}

// lib/types/canvas.ts

export interface CanvasResponse {
  id: string;
  tenant_id: string;
  user_id: string;
  title: string | null;
  content: string | null;
  html_content: string | null;
  save_state: string | null;
  created_at: string;
  updated_at: string;
}
```

### 6.12 SSE Stream Events

```typescript
// lib/types/stream.ts

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

export interface ContentDeltaEvent {
  event_type: "content_delta";
  text: string;
}

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
  member: string | null;
}

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

// -- User push events --

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
```

### 6.13 Request Types

```typescript
// lib/types/requests.ts

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

export interface CreateConversation {
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

export interface SearchRequest {
  query: string;
  categories?: KnowledgeBaseCategory[];
  knowledge_base_ids?: string[];
  limit?: number;
  similarity_threshold?: number;
}

export interface CreateKnowledgeBase {
  name: string;
  category: KnowledgeBaseCategory;
  source_type: KnowledgeBaseSourceType;
}

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

export interface CreateGuardrail {
  name: string;
  description?: string;
  configuration_rules?: Record<string, unknown>;
}

export interface UpdateGuardrail {
  name?: string;
  description?: string;
  configuration_rules?: Record<string, unknown>;
}

export interface CreatePolicyDefinition {
  name: string;
  uri: string;
  status?: "active" | "inactive";
  group_id?: string;
  description?: string;
  is_required?: boolean;
  review_cycle?: ReviewCycle;
  name_variants?: string[];
  scoring_criteria?: Record<string, unknown>;
  compliance_criteria?: Record<string, unknown>;
  required_sections?: string[];
  legislation_references?: Record<string, unknown>[];
  topic_ids?: string[];
}

export interface UpdatePolicyDefinition {
  name?: string;
  status?: "active" | "inactive";
  group_id?: string;
  description?: string;
  is_required?: boolean;
  review_cycle?: ReviewCycle;
  name_variants?: string[];
  scoring_criteria?: Record<string, unknown>;
  compliance_criteria?: Record<string, unknown>;
  required_sections?: string[];
  legislation_references?: Record<string, unknown>[];
  topic_ids?: string[];
}

export interface CreateFeedback {
  rating: FeedbackRating;
  comment?: string;
}

export interface UpdateAlert {
  status: AlertStatus;
}

export interface CreateCanvas {
  title?: string;
  content?: string;
  html_content?: string;
}

export interface UpdateCanvas {
  title?: string;
  content?: string;
  html_content?: string;
  save_state?: string;
}

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

export interface UpdateTenant {
  name?: string;
  industry_vertical?: string;
  branding_config?: Record<string, unknown>;
  ai_config?: Record<string, unknown>;
  news_feed_urls?: string[];
  external_source_integrations?: Record<string, unknown>[];
}
```

### 6.14 Health Check

```typescript
// lib/types/health.ts

export interface HealthResponse {
  status: "healthy" | "degraded" | "unhealthy";
  database: "connected" | "error";
  qdrant: "connected" | "error";
  redis: "connected" | "error";
  lex: "connected" | "fallback" | "error";
  version: string;
}
```
