# YourAI — Claude Code Development Operator's Guide

> **Who this is for**: You, the programme manager. This is your playbook for running the development process using Claude Code agents.

---

## 1. Prerequisites

### 1.1 What You Need Installed
- Claude Code CLI (`brew install claude-code` or `winget install Anthropic.ClaudeCode`)
- Claude Pro, Max, or Teams subscription (Max recommended for Opus access)
- Git
- Docker Desktop (for Postgres, Redis, Qdrant)
- Python 3.12+ with `uv` (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Node.js 20+ with `pnpm` (`npm install -g pnpm`)

### 1.2 Recommended Claude Code Model
- Use **Opus 4.5** for architecture and AI engine work (WP0, WP5)
- Use **Sonnet 4.5** for well-defined implementation work (WP1, WP2, WP3, WP7)
- Set via: `export ANTHROPIC_MODEL=claude-opus-4-6` or `export ANTHROPIC_MODEL=claude-sonnet-4-5-20250929`

---

## 2. Initial Setup (Do This Once)

### Step 1: Create the repository
```bash
mkdir yourai && cd yourai
git init
```

### Step 2: Copy the handover pack
Copy all files from this handover pack into the repo root:
```
yourai/
├── CLAUDE.md
├── .claude/
│   ├── settings.json
│   ├── agents/
│   │   ├── architect.md
│   │   ├── core-platform.md
│   │   ├── data-pipeline.md
│   │   ├── ai-engine.md
│   │   └── frontend.md
│   └── commands/
│       ├── start-wp.md
│       ├── review-architecture.md
│       └── check-integration.md
├── docs/
│   ├── FUNCTIONAL_SPEC_V2.md    ← Copy from your project files
│   └── architecture/
│       ├── TECH_DECISIONS.md
│       ├── DATABASE_SCHEMA.sql  ← Will be created in Phase 0
│       ├── API_CONTRACTS.md     ← Will be created in Phase 0
│       └── PROGRESS.md          ← Will be created in Phase 0
└── infrastructure/
    └── docker-compose.yml       ← Will be created in Phase 0
```

### Step 3: Copy the functional spec
```bash
cp /path/to/FUNCTIONAL_SPECIFICATION_YOURAI_V2.md docs/FUNCTIONAL_SPEC_V2.md
```

### Step 4: Initial commit
```bash
git add -A
git commit -m "Initial project setup with Claude Code handover pack"
```

---

## 3. Phase 0: Architecture (You + Architect Agent)

**Model**: Opus 4.5
**Duration**: 1-2 weeks
**Branch**: `wp0/architecture`

This phase creates the foundational artifacts that all other agents depend on. You drive this with Claude Code's architect agent.

### Session 1: Database Schema

```bash
git checkout -b wp0/architecture
export ANTHROPIC_MODEL=claude-opus-4-6
claude
```

In Claude Code:
```
Read docs/FUNCTIONAL_SPEC_V2.md Section 11 (Data Model) and docs/architecture/TECH_DECISIONS.md.

Design the complete PostgreSQL database schema for YourAI. Requirements:
- All tables from the spec's data model
- UUIDv7 primary keys
- tenant_id on all tenant-scoped tables
- RLS policies for every tenant-scoped table
- created_at/updated_at timestamps
- Proper foreign keys and indexes
- JSONB for flexible config fields (branding, review results)
- Enum types for statuses (user_status, document_processing_state, etc.)

Write the schema to docs/architecture/DATABASE_SCHEMA.sql.
Present a plan first, then implement.
```

**Review gate**: Read the schema carefully. Check that:
- Every table in Spec §11 exists
- RLS policies are correct
- Relationships match the spec's entity diagram
- Indexes exist for common query patterns

### Session 2: API Contracts

```
Read the agent files in .claude/agents/ to understand the interfaces each agent provides and consumes.
Read docs/architecture/TECH_DECISIONS.md.

Create docs/architecture/API_CONTRACTS.md defining:
1. All Python service interfaces (classes, method signatures, return types) that cross WP boundaries
2. All REST API endpoint definitions (path, method, request/response schemas)
3. All SSE event type definitions
4. All Celery task signatures

Use Pydantic model definitions for request/response schemas.
Include TypeScript equivalents for types the frontend needs.
```

### Session 3: Project Scaffolding

```
Set up the monorepo structure:

1. Backend (Python/FastAPI):
   - Create pyproject.toml with all dependencies from TECH_DECISIONS.md
   - Set up src/yourai/ package with empty __init__.py files for all modules
   - Set up alembic configuration
   - Create initial migration from DATABASE_SCHEMA.sql
   - Set up pytest configuration (conftest.py with test database, fixtures)
   - Set up ruff and mypy configuration

2. Frontend (Next.js):
   - Create Next.js 15 app with TypeScript, Tailwind, shadcn/ui
   - Set up project structure from CLAUDE.md
   - Configure ESLint, Prettier, Vitest
   - Create base API client stub

3. Infrastructure:
   - Create docker-compose.yml (Postgres 16, Redis, Qdrant)
   - Create docker-compose.lex.yml (self-hosted Lex stack)
   - Create .env.example with all required environment variables

4. Create docs/architecture/PROGRESS.md to track WP status

Verify: `docker compose up -d` starts all services,
`cd backend && uv run pytest` runs (even if no tests yet),
`cd frontend && pnpm dev` starts the dev server.
```

### Session 4: Lex Data Ingestion (Start Early)

This takes 8+ hours, so kick it off now:

```bash
# In a separate terminal
git clone https://github.com/i-dot-ai/lex.git infrastructure/lex
cd infrastructure/lex
cp .env.example .env
# Edit .env: add Azure OpenAI credentials
docker compose up -d
make ingest-all-full
# This runs for 8+ hours — let it run overnight
```

### Phase 0 Completion Checklist
- [ ] `docs/architecture/DATABASE_SCHEMA.sql` — reviewed and committed
- [ ] `docs/architecture/API_CONTRACTS.md` — reviewed and committed
- [ ] `docs/architecture/TECH_DECISIONS.md` — any updates committed
- [ ] `docs/architecture/PROGRESS.md` — created with all WPs listed
- [ ] Backend scaffolding: `uv run pytest` passes (no tests yet, but no errors)
- [ ] Frontend scaffolding: `pnpm dev` starts
- [ ] Docker Compose: Postgres, Redis, Qdrant all healthy
- [ ] Lex data ingestion: started (running in background)
- [ ] Initial migration: `uv run alembic upgrade head` creates all tables

```bash
git add -A
git commit -m "[WP0] Architecture scaffolding complete"
git checkout main
git merge wp0/architecture
```

---

## 4. Phase 1: Foundations (Parallel Agents)

**Duration**: Weeks 3-4
**Running in parallel**: WP1 + WP2

### WP1: Multi-Tenant Core

```bash
git checkout -b wp1/tenant-core
export ANTHROPIC_MODEL=claude-sonnet-4-5-20250929
claude
```

In Claude Code:
```
/start-wp

Work package: WP1

Read the core-platform agent briefing at .claude/agents/core-platform.md.
This is your scope. Build everything described there.

Start with:
1. Database models (SQLAlchemy 2.0) for tenants, users, roles, permissions
2. Service layer (TenantService, UserService, AuthService, PermissionChecker)
3. Middleware (tenant resolution, auth verification, RLS context setting)
4. API routes (auth, users, tenants)
5. Tests

Present your implementation plan first.
```

**Key checkpoints during this session**:
- After models: verify RLS policies are applied via migration
- After services: run unit tests
- After middleware: test that RLS actually blocks cross-tenant access
- After routes: test full auth flow with mock IdP

### WP2: Real-Time Communication

Can run in a **separate terminal** simultaneously:

```bash
git checkout -b wp2/realtime
export ANTHROPIC_MODEL=claude-sonnet-4-5-20250929
claude
```

```
Build the SSE streaming infrastructure.

Read docs/architecture/API_CONTRACTS.md for the event type definitions.
Read docs/architecture/TECH_DECISIONS.md §6 (SSE).

Build in backend/src/yourai/api/:
1. SSE endpoint handler that manages client connections
2. Event publishing mechanism (other services publish, SSE endpoint streams)
3. Channel management (per-user, per-conversation, per-policy-review, per-knowledge-base)
4. Connection authentication (verify JWT, scope to tenant)
5. Reconnection support with event replay (within a configurable window)
6. Typed event models matching the spec's event catalogue (Section 3.1.10)

Use Redis pub/sub as the event transport (Celery's Redis instance).

Tests:
- Publish event → client receives it
- Cross-tenant isolation (events don't leak)
- Reconnection replays missed events
- Authentication required
```

### Phase 1 Gate Review

Before proceeding, run the integration check:

```bash
git checkout main
git merge wp1/tenant-core
git merge wp2/realtime
claude
```

```
/check-integration

Specifically verify:
1. Auth middleware works end-to-end (token → user → tenant → RLS)
2. SSE endpoint uses auth middleware correctly
3. RLS blocks cross-tenant data access at the database level
4. Run all tests: cd backend && uv run pytest
```

---

## 5. Phase 2: Data & Search (Weeks 5-6)

### WP3: Document Processing Pipeline

```bash
git checkout -b wp3/document-pipeline
export ANTHROPIC_MODEL=claude-sonnet-4-5-20250929
claude
```

```
/start-wp

Work package: WP3

Read .claude/agents/data-pipeline.md for your full scope.
You depend on WP1 (core.middleware) which is now merged to main.

Build the complete document processing pipeline and hybrid search.
Start with the models and state machine, then extraction, chunking,
embedding, indexing, and finally search.
```

### WP4: Lex Integration (continued)

In a separate terminal:

```bash
git checkout -b wp4/lex-integration
claude
```

```
The self-hosted Lex instance should now be running with data ingested.
Verify: curl http://localhost:8080/healthcheck

Build the Lex integration layer in backend/src/yourai/knowledge/:
1. lex_mcp.py — MCP client for interactive agent tool calls
2. lex_rest.py — REST client for deterministic lookups
3. lex_health.py — Health check + failover (self-hosted primary, public fallback)
4. lex_changes.py — Weekly Parquet diff for regulatory change detection

Read docs/architecture/TECH_DECISIONS.md §8 for binding decisions.

Test: search for "Housing Act 1985" via MCP tools and verify results.
Test: failover by stopping self-hosted Lex and verifying traffic routes to public API.
```

---

## 6. Phase 3: AI Core (Weeks 7-12)

**Model**: Switch to Opus for this phase — it's the most complex.

```bash
git checkout -b wp5/ai-engine
export ANTHROPIC_MODEL=claude-opus-4-6
claude
```

```
/start-wp

Work package: WP5

Read .claude/agents/ai-engine.md for your full scope.
This is the most complex work package. You'll need multiple sessions.

SESSION 1 — Framework:
Build the agent framework: model routing, invocation lifecycle,
SSE streaming integration, persona loading, conversation history management.
Get a basic end-to-end flow working: user message → Router → simple response streamed back.

Do NOT build workers or verification yet. Get the framework right first.
```

After Session 1 works, continue:

```
SESSION 2 — Knowledge Workers:
Add the parallel knowledge workers:
- Policy Worker (calls SearchService from WP3)
- Legislation Worker (calls Lex MCP from WP4)
- Case Law Worker (calls Lex MCP from WP4)

Test: ask a housing legislation question → workers retrieve relevant sources →
orchestrator synthesises a response with inline citations.
```

```
SESSION 3 — Citation Verification:
Build the Citation Verification Agent.
This runs AFTER the primary response is generated.
It independently verifies every citation via Lex API lookup.

Test: fabricate a fake section number in a response → verification catches it and marks it as Removed.
Test: cite a real section → verification marks it as Verified.
```

```
SESSION 4 — Polish:
Add: semantic cache, confidence scoring, skills pattern,
mandatory disclaimers, title generation agent, QA agent (testing mode).

Run full integration test: question → routing → workers → synthesis → verification → streaming.
```

---

## 7. Phase 4: Frontend (Weeks 6-14, partially parallel)

### WP7a+7b can start during Phase 2

```bash
git checkout -b wp7/frontend
export ANTHROPIC_MODEL=claude-sonnet-4-5-20250929
claude
```

```
/start-wp

Work package: WP7

Read .claude/agents/frontend.md for your full scope.

Start with WP7a (shell and navigation):
- Auth flow (login page, OAuth callback, token storage, redirect)
- App shell with sidebar
- Tenant branding application
- Responsive layout

Then WP7b (conversation interface):
- Chat input with file attachment
- Message list rendering
- SSE streaming consumption — wire up to the backend SSE endpoint
- Citation display with verification badges
- Confidence indicators
- Persona selector

Mock the AI responses initially if the backend isn't ready yet.
Use the event type definitions from docs/architecture/API_CONTRACTS.md.
```

---

## 8. How to Manage Context in Long Sessions

Claude Code's context window fills up. Here's how to manage it:

### Use subagents for research
```
Use a subagent to investigate how the Lex MCP tools work.
Read the Lex repo documentation and report back what tools are available
and how to call them from Python.
```

### Compact strategically
When you see the "context window running low" warning:
- Finish the current logical unit of work
- Commit your changes
- Start a new session

### Split sessions by logical units
Don't try to build an entire WP in one session. Split by:
- Models + migrations (session 1)
- Service layer (session 2)
- API routes (session 3)
- Tests (session 4)

### Use Plan Mode for complex work
For WP5 especially:
```
Plan how you would implement the multi-agent orchestration system.
Consider: parallel worker execution, error handling when one worker fails,
token budget management, streaming events from multiple workers.
Write the plan to docs/work-packages/WP5_PLAN.md.
```

Then in a new session:
```
Read docs/work-packages/WP5_PLAN.md and implement it.
```

---

## 9. Review Cadence

### Daily
- Check PROGRESS.md — update WP status
- Run `cd backend && uv run pytest` — all tests pass?
- Run `cd frontend && pnpm type-check` — no type errors?

### At Each Phase Gate
- Run `/review-architecture` in Claude Code
- Run `/check-integration` in Claude Code
- Manual review of key security concerns:
  - RLS policies active and tested
  - Auth flow correct
  - No hardcoded secrets
  - Tenant isolation verified

### Before MVP Demo
- Full E2E test: create tenant → create user → login → upload document →
  ask question → get cited response → verify citations are real
- Accessibility audit (automated + manual keyboard testing)
- Security review (auth flow, RLS, data isolation)

---

## 10. Tracking Progress

Update `docs/architecture/PROGRESS.md` as you go:

```markdown
# YourAI — Development Progress

## Current Phase: 1 — Foundations

| WP | Name | Status | Branch | Notes |
|----|------|--------|--------|-------|
| WP0 | Architecture | ✅ Complete | merged | Schema, contracts, scaffolding |
| WP1 | Multi-Tenant Core | 🔄 In Progress | wp1/tenant-core | Models done, services in progress |
| WP2 | Real-Time Comms | ⏳ Not Started | — | |
| WP3 | Document Pipeline | ⏳ Not Started | — | Blocked by WP1 |
| WP4 | Lex Integration | 🔄 Data Ingesting | — | Lex running, 6hr remaining |
| WP5 | AI Engine | ⏳ Not Started | — | Blocked by WP3+WP4 |
| WP6 | Policy Review | ⏳ Not Started | — | Blocked by WP5 |
| WP7 | Frontend | ⏳ Not Started | — | WP7a can start after WP1 |
| WP8 | Regulatory Monitoring | ⏳ Post-MVP | — | |
| WP9 | Billing | ⏳ Post-MVP | — | |
| WP10 | Reporting | ⏳ Post-MVP | — | |
| WP11 | GDPR | ⏳ Post-MVP | — | |
| WP12 | Observability | ⏳ Post-MVP | — | |

## Gate Reviews
- [ ] G0: Architecture — WP0 complete
- [ ] G1: Foundation — WP1+WP2 integrated
- [ ] G2: Data Pipeline — WP3+WP4 integrated
- [ ] G3: AI Core — WP5 working end-to-end
- [ ] G4: MVP — Full conversation flow
- [ ] G5: Launch — Security, GDPR, accessibility
```

---

## 11. Documenting the Experiment

Since this is also an experiment in agent-driven development, log:

### After each Claude Code session, note:
- **Session ID**: WP + session number (e.g., WP1-S3)
- **Duration**: How long the session ran
- **Model used**: Opus/Sonnet
- **What was accomplished**: What got built
- **Human interventions**: Times you corrected Claude, and what about
- **Quality assessment**: How good was the output? (1-5)
- **Context management**: Did context run out? How was it handled?
- **Surprises**: Anything unexpected (good or bad)

Create `docs/experiment-log/` and add entries as you go.

---

## 12. Emergency Procedures

### Claude Code produces broken code
```bash
git stash                    # Save current changes
git checkout main            # Return to known-good state
git checkout -b wp<N>/retry  # Fresh branch
# Start a new Claude Code session with clearer instructions
```

### Tests start failing across WPs
```bash
claude
/check-integration
# This will identify which interface contract is broken
```

### Lex self-hosted instance fails
```
The Lex self-hosted instance is down. Check:
1. docker compose -f docker-compose.lex.yml logs
2. Is Qdrant healthy? curl http://localhost:6333/health
3. Is the Lex API healthy? curl http://localhost:8080/healthcheck
4. If data is corrupted: docker compose -f docker-compose.lex.yml down -v && docker compose -f docker-compose.lex.yml up -d && make ingest-all-full
```

### Context window exhausted mid-task
1. Commit whatever is working: `git add -A && git commit -m "WIP: [description]"`
2. Start a new Claude Code session
3. Tell Claude: "Read the git log and the current state of files in [directory] to understand where we left off. Continue from there."
