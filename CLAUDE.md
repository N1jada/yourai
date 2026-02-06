# YourAI

White-label, multi-tenant AI compliance platform for regulated industries. Built on Anthropic API (Claude), FastAPI, Next.js, PostgreSQL, Qdrant.

## Stack

- **Backend**: Python 3.12+, FastAPI, SQLAlchemy 2.0, Alembic (migrations), Celery + Redis (queues)
- **Frontend**: Next.js 15 (App Router), TypeScript, React 19, Tailwind CSS
- **Database**: PostgreSQL 16 with Row-Level Security
- **Vector DB**: Qdrant (tenant-namespaced)
- **Real-time**: Server-Sent Events (SSE)
- **External**: Anthropic API, Lex API (self-hosted), Parliament MCP (optional)
- **Package managers**: uv (Python), pnpm (Node)

## Project Structure

```
yourai/
├── CLAUDE.md                    # You are here
├── docs/
│   ├── FUNCTIONAL_SPEC_V2.md    # Full functional specification
│   ├── architecture/
│   │   ├── TECH_DECISIONS.md    # Technology decision record
│   │   ├── DATABASE_SCHEMA.sql  # Canonical schema
│   │   └── API_CONTRACTS.md     # Interface definitions between services
│   └── work-packages/           # Detailed WP briefings
├── backend/                     # FastAPI application
│   ├── CLAUDE.md                # Backend-specific instructions
│   ├── src/yourai/
│   │   ├── core/                # Tenant, auth, RBAC, config
│   │   ├── knowledge/           # Document processing, search, embeddings
│   │   ├── agents/              # AI engine, multi-agent orchestration
│   │   ├── policy/              # Policy review, ontology, compliance
│   │   ├── billing/             # Credits, usage tracking
│   │   ├── monitoring/          # Regulatory change detection
│   │   └── api/                 # FastAPI routes, middleware, SSE
│   ├── tests/
│   ├── alembic/                 # Database migrations
│   └── pyproject.toml
├── frontend/                    # Next.js application
│   ├── CLAUDE.md                # Frontend-specific instructions
│   ├── src/
│   │   ├── app/                 # Next.js App Router pages
│   │   ├── components/          # React components
│   │   ├── lib/                 # API clients, hooks, utilities
│   │   └── stores/              # State management
│   ├── package.json
│   └── tsconfig.json
├── infrastructure/
│   ├── docker-compose.yml       # Local dev environment
│   ├── docker-compose.lex.yml   # Self-hosted Lex stack
│   └── Dockerfiles/
└── .claude/                     # Claude Code configuration
    ├── agents/                  # Sub-agent definitions
    ├── commands/                # Custom slash commands
    └── settings.json            # Hooks and permissions
```

## Common Commands

### Backend
```bash
cd backend
uv run pytest                           # Run all tests
uv run pytest tests/unit/               # Unit tests only
uv run pytest tests/integration/        # Integration tests only
uv run pytest -k "test_name" -x         # Single test, stop on failure
uv run alembic upgrade head             # Apply migrations
uv run alembic revision --autogenerate -m "description"  # New migration
uv run ruff check src/                  # Lint
uv run ruff format src/                 # Format
uv run mypy src/                        # Type check
uv run uvicorn yourai.api.main:app --reload  # Dev server (port 8000)
```

### Frontend
```bash
cd frontend
pnpm dev                                # Dev server (port 3000)
pnpm build                              # Production build
pnpm lint                               # ESLint
pnpm type-check                         # TypeScript check
pnpm test                               # Vitest
pnpm test -- --run tests/unit/          # Unit tests only
```

### Infrastructure
```bash
docker compose up -d                    # Start Postgres, Redis, Qdrant
docker compose -f docker-compose.lex.yml up -d  # Start self-hosted Lex
docker compose logs -f postgres         # Follow Postgres logs
```

## Coding Standards

### Python (Backend)
- Python 3.12+, strict typing with mypy
- Use `async def` for all API endpoints and database operations
- SQLAlchemy 2.0 style (mapped_column, not Column)
- Every database query MUST include `tenant_id` filter — see `docs/architecture/TECH_DECISIONS.md` §Tenant Isolation
- Pydantic v2 for all request/response schemas
- Use structured logging (structlog) with `tenant_id`, `user_id`, `request_id` in every log
- British English in all user-facing strings and AI prompts
- Test files mirror source structure: `src/yourai/core/auth.py` → `tests/unit/core/test_auth.py`

### TypeScript (Frontend)
- Strict TypeScript, no `any`
- React Server Components by default, `"use client"` only when needed
- Zustand for client-side state
- TanStack Query for server state
- All API calls go through `lib/api/` client — never fetch directly from components
- WCAG 2.2 AA compliance — see `docs/architecture/TECH_DECISIONS.md` §Accessibility

### Git Workflow
- Branch per work package: `wp1/tenant-core`, `wp3/document-pipeline`
- Commit messages: `[WP1] Add tenant RBAC middleware`
- Never commit directly to main
- Run `uv run pytest && cd frontend && pnpm type-check` before pushing

## Architecture Decisions

See `docs/architecture/TECH_DECISIONS.md` for the full record. Key decisions:
- **Tenant isolation**: RLS + application-level filtering (belt and braces)
- **Vector namespacing**: Qdrant collection per tenant, not shared collection with metadata filter
- **Embedding versioning**: `{model}:{version}` tag on every vector
- **AI model routing**: Haiku for classification/routing, Sonnet for analysis, Opus optional for synthesis
- **Lex integration**: Self-hosted primary, public API fallback
- **Search**: Hybrid (vector + BM25) with RRF fusion and cross-encoder reranking

## Work Package Sequence

This project is built in phases. See `docs/work-packages/` for detailed briefings.
Current phase and active WPs are tracked in `docs/architecture/PROGRESS.md`.
