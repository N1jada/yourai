# YourAI — Technology Decision Record

> This document records all binding technology and architecture decisions.
> Every Claude Code agent MUST follow these decisions. Do not deviate without human approval.

---

## 1. Backend Framework: FastAPI (Python 3.12+)

**Decision**: FastAPI with async SQLAlchemy, Pydantic v2, uvicorn.

**Rationale**:
- Aligns with Lex API ecosystem (Python, FastMCP)
- Excellent async support for streaming SSE responses
- Pydantic v2 for request/response validation
- Strong typing with mypy
- MCP client libraries available in Python (FastMCP)

**Key libraries**:
- `fastapi` — web framework
- `sqlalchemy[asyncio]` — ORM (2.0 style)
- `alembic` — migrations
- `pydantic` v2 — schemas
- `anthropic` — Claude API client
- `qdrant-client` — vector DB
- `celery[redis]` — background task queue
- `structlog` — structured logging
- `httpx` — async HTTP client
- `python-multipart` — file uploads
- `python-jose[cryptography]` — JWT handling
- `passlib` — password hashing (if needed)
- `mcp` — MCP client for Lex integration

---

## 2. Frontend Framework: Next.js 15 (App Router)

**Decision**: Next.js with TypeScript, React 19, Tailwind CSS, shadcn/ui.

**Rationale**:
- Server-side rendering for initial load performance
- App Router for layout nesting (sidebar + content)
- Native SSE/streaming support via ReadableStream
- shadcn/ui provides accessible, customisable components (WCAG 2.2 AA)

**Key libraries**:
- `next` 15 — framework
- `react` 19 — UI library
- `tailwindcss` — utility CSS
- `@tanstack/react-query` — server state management
- `zustand` — client state management
- `zod` — runtime schema validation
- `lucide-react` — icons
- `react-markdown` + `remark-gfm` — markdown rendering
- `@radix-ui/*` — accessible primitives (via shadcn/ui)

---

## 3. Database: PostgreSQL 16 with Row-Level Security

**Decision**: PostgreSQL with RLS policies on every tenant-scoped table.

### Tenant Isolation Strategy (CRITICAL)

Every table with tenant-scoped data has:
1. A `tenant_id UUID NOT NULL` column
2. An RLS policy: `CREATE POLICY tenant_isolation ON <table> USING (tenant_id = current_setting('app.current_tenant_id')::uuid)`
3. Application middleware sets `SET LOCAL app.current_tenant_id = '<uuid>'` at the start of every request

This is belt-and-braces: the application code ALSO filters by tenant_id, but RLS is the safety net.

### Connection Pooling
- Use `asyncpg` via SQLAlchemy async engine
- Connection pool: min 5, max 20 per worker
- Statement timeout: 30 seconds

### Key Conventions
- All primary keys: `UUID` (generated as UUIDv7 for sortability)
- All tables have: `created_at TIMESTAMPTZ DEFAULT NOW()`, `updated_at TIMESTAMPTZ DEFAULT NOW()`
- Soft delete via `deleted_at TIMESTAMPTZ NULL` where needed (users, conversations)
- Use `JSONB` for flexible schema fields (tenant branding config, policy review results)

---

## 4. Vector Database: Qdrant

**Decision**: Qdrant with collection-per-tenant namespace isolation.

### Namespace Strategy
- Each tenant gets a separate Qdrant collection: `tenant_{tenant_id}_documents`
- This provides hard isolation — no risk of cross-tenant vector leakage
- Trade-off: more collections to manage, but isolation is non-negotiable for regulated industries

### Embedding Configuration
- Default model: `text-embedding-3-large` (OpenAI) or Voyage 3 Large — decision deferred to implementation
- Dimensions: model-dependent (1536 or 1024)
- Every vector tagged with: `embedding_model`, `embedding_version`, `document_id`, `chunk_index`
- BM25 keyword index: Qdrant's built-in full-text payload index

### Search Pipeline
1. Vector search → top 200 candidates
2. BM25 keyword search → top 200 candidates
3. Reciprocal Rank Fusion (RRF) to merge
4. Cross-encoder reranking → top 5-10 results

---

## 5. Background Processing: Celery + Redis

**Decision**: Celery with Redis broker, dedicated queues per concern.

### Queue Configuration
```python
CELERY_QUEUES = {
    "default": {},
    "knowledge_ingest": {"routing_key": "knowledge.*"},
    "interaction": {"routing_key": "interaction.*"},
    "verification": {"routing_key": "verification.*"},
    "monitoring": {"routing_key": "monitoring.*"},
    "reporting": {"routing_key": "reporting.*"},
}
```

### Task Patterns
- Document processing: chain of tasks (extract → chunk → contextualise → embed → index)
- AI invocations: single long-running task with SSE streaming callback
- Retry: exponential backoff (1s, 2s, 4s, max 30s) with jitter, max 3 retries
- Dead letter: after 3 failures, move to DLQ with full diagnostic context

---

## 6. Real-Time Communication: Server-Sent Events (SSE)

**Decision**: SSE over WebSocket for AI response streaming.

**Rationale**:
- One-way server→client flow matches AI streaming pattern
- Simpler infrastructure (no WebSocket upgrade, works through more proxies/load balancers)
- Native browser support via EventSource API
- Easy to add event types without protocol changes

### Event Format
```
event: content_delta
data: {"text": "The Housing Act 1985..."}

event: legal_source
data: {"act_name": "Housing Act 1985", "section": "s.1", "uri": "...", "verification_status": "verified"}

event: confidence_update
data: {"level": "high", "reason": "Multiple corroborating sources"}
```

### Endpoint Pattern
- `GET /api/v1/conversations/{id}/stream` — SSE endpoint for conversation
- `GET /api/v1/policy-reviews/{id}/stream` — SSE endpoint for policy review
- Client sends messages via `POST /api/v1/conversations/{id}/messages`

---

## 7. AI Model Routing

**Decision**: Route to different Claude model tiers based on task complexity.

| Task | Model | Env Var |
|------|-------|---------|
| Query classification, routing | `claude-haiku-4-5-20251001` | `YOURAI_MODEL_FAST` |
| Title generation | `claude-haiku-4-5-20251001` | `YOURAI_MODEL_FAST` |
| Contextual chunk enrichment | `claude-haiku-4-5-20251001` | `YOURAI_MODEL_FAST` |
| Primary conversation analysis | `claude-sonnet-4-5-20250929` | `YOURAI_MODEL_STANDARD` |
| Citation verification | `claude-sonnet-4-5-20250929` | `YOURAI_MODEL_STANDARD` |
| Policy review | `claude-sonnet-4-5-20250929` | `YOURAI_MODEL_STANDARD` |
| Complex synthesis (Enterprise) | `claude-opus-4-6` | `YOURAI_MODEL_ADVANCED` |

---

## 8. Lex API Integration

**Decision**: Self-hosted Lex as primary, public API as fallback.

### Self-Hosted
- Deployed via Docker Compose alongside YourAI
- Qdrant instance shared or separate (separate recommended for isolation)
- Weekly Parquet data refresh automated via Celery beat task
- No rate limits (internal network)

### Fallback
- Public endpoint: `https://lex.lab.i.ai.gov.uk/mcp`
- Rate limited: 60 req/min, 1000 req/hr
- Health check every 30 seconds on self-hosted; auto-failover on 3 consecutive failures

### Connection Modes
- **MCP** (via `mcp` Python library): for AI agent tool calls during conversation
- **REST** (via `httpx`): for deterministic operations (specific legislation lookup, full text retrieval, change detection)

---

## 9. Authentication: External IdP (OAuth2/OIDC)

**Decision**: Delegate authentication to an external identity provider.

- Default recommendation: Auth0 or Keycloak (self-hosted)
- PKCE flow for browser clients
- JWT validation in FastAPI middleware
- `tenant_id` extracted from JWT custom claims or looked up from user record
- 12-hour session, silent refresh via refresh token

---

## 10. Accessibility: WCAG 2.2 AA

**Decision**: All UI must meet WCAG 2.2 Level AA from the start.

Key requirements embedded in frontend development:
- Chat container: `role="log"` with `aria-label="Conversation"`
- New messages: `aria-live="polite"` announcements
- RAG ratings: text labels + colour (never colour-only)
- Keyboard operability for all interactions
- 4.5:1 contrast ratio for normal text
- `prefers-reduced-motion` respected for streaming animations
- Drag-and-drop has keyboard/button alternative

---

## 11. Logging & Observability

**Decision**: Structured JSON logging via structlog, OpenTelemetry tracing.

### Log Format
```json
{
  "timestamp": "2025-02-05T12:00:00Z",
  "level": "info",
  "event": "agent_invocation_started",
  "tenant_id": "uuid",
  "user_id": "uuid",
  "request_id": "uuid",
  "conversation_id": "uuid",
  "agent": "router",
  "model": "claude-haiku-4-5-20251001"
}
```

Every log line MUST include: `tenant_id`, `request_id`. Include `user_id` and `conversation_id` where available.

### Tracing
- OpenTelemetry SDK with OTLP exporter
- Spans for: API request → agent invocation → tool call → LLM API call
- Trace ID propagated through Celery tasks

---

## 12. British English

**Decision**: All user-facing text, AI prompts, error messages, and documentation use British English.

- "colour" not "color", "organisation" not "organization", "authorisation" not "authorization"
- System prompt includes: "Always respond in British English spelling and conventions."
- UI copy reviewed for British English consistency
