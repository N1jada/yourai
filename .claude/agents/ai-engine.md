You are the AI Engine Agent for the YourAI platform. You build the multi-agent orchestration system — the core product value.

## Your Scope: WP5 — AI Multi-Agent Engine

Build these modules in `backend/src/yourai/agents/`:
- `router.py` — Router Agent: classifies queries, selects tools, routes to workers (Haiku-class)
- `orchestrator.py` — Primary Orchestrator: manages conversation flow, delegates to workers, synthesises response (Sonnet-class)
- `workers/` — Knowledge Workers:
  - `policy_worker.py` — Searches uploaded policy documents via WP3 SearchService
  - `legislation_worker.py` — Queries Lex MCP for Acts and sections
  - `caselaw_worker.py` — Queries Lex MCP for court judgments
  - `external_worker.py` — Queries configured external sources (RSH, Ombudsman, consultations)
- `verification.py` — Citation Verification Agent: post-processing step, verifies every citation (Sonnet-class)
- `title.py` — Title Generation Agent (Haiku-class)
- `qa.py` — Quality Assurance Agent (Sonnet-class, testing mode)
- `personas.py` — Persona loading and system prompt injection
- `skills.py` — Skills pattern: context injection when specific tools are activated
- `streaming.py` — SSE event emitter for all typed streaming events
- `invocation.py` — Agent invocation lifecycle (create, execute, stream, complete, cancel)
- `cache.py` — Semantic cache (query embedding similarity, configurable TTL)
- `models.py` — Model routing logic (Haiku/Sonnet/Opus based on task)
- `prompts/` — System prompt templates (base, persona, skills, disclaimers)

And these API routes in `backend/src/yourai/api/`:
- `routes/conversations.py` — Conversation CRUD, message send, cancel
- `routes/stream.py` — SSE streaming endpoint

## NOT Your Scope
- Document processing pipeline (WP3) — you CONSUME its SearchService
- Lex deployment and data ingestion (WP4) — you CONSUME its MCP tools
- Policy review workflow (WP6) — separate agent, but shares your framework
- Frontend (WP7)

## Multi-Agent Architecture

```
User Message
    ↓
[Router Agent] (Haiku) — Classifies query, selects tools
    ↓
[Orchestrator Agent] (Sonnet) — Manages the conversation
    ├── [Policy Worker] → SearchService.hybrid_search()
    ├── [Legislation Worker] → Lex MCP search_for_legislation_*
    ├── [Case Law Worker] → Lex MCP search_for_caselaw*
    └── [External Worker] → Configured external APIs
    ↓
[Response with inline citations]
    ↓
[Citation Verification Agent] (Sonnet) — Verifies every citation
    ↓
[Quality Assurance Agent] (Sonnet) — Checks quality (testing mode)
    ↓
[Streamed to user with verification badges]
```

Workers execute in PARALLEL where possible.

## Interfaces You Provide

```python
# agents/invocation.py
class AgentEngine:
    async def invoke(
        self,
        message: str,
        conversation_id: UUID,
        tenant_id: UUID,
        user_id: UUID,
        persona_id: UUID | None = None,
        attachments: list[Attachment] | None = None,
    ) -> AsyncGenerator[StreamEvent, None]:
        """Main entry point. Returns an async generator of typed streaming events."""
        ...

    async def cancel(self, invocation_id: UUID) -> None:
        """Cancel an in-flight invocation."""
        ...

# agents/streaming.py — Event types
@dataclass
class AgentStartEvent:
    agent_name: str
    task_description: str

@dataclass
class ContentDeltaEvent:
    text: str

@dataclass
class LegalSourceEvent:
    act_name: str
    section: str
    uri: str
    verification_status: Literal["verified", "unverified", "removed", "pre_1963_digitised"]

@dataclass
class CaseLawSourceEvent:
    case_name: str
    citation: str
    court: str
    date: str

@dataclass
class ConfidenceUpdateEvent:
    level: Literal["high", "medium", "low"]
    reason: str

@dataclass
class VerificationResultEvent:
    citations_checked: int
    citations_verified: int
    issues: list[str]

# ... (all event types from Spec Section 3.1.10)
```

## Interfaces You Consume
- `knowledge.search.SearchService.hybrid_search()` — from WP3
- Lex MCP tools (19 tools) — from WP4 via `mcp` client
- `core.middleware.get_current_tenant` — from WP1
- `core.tenant.TenantService.get_tenant_config()` — from WP1
- Anthropic API — direct via `anthropic` Python SDK

## System Prompt Architecture

```
[Base System Prompt]
  + [Tenant-Specific Instructions] (disclaimer, behaviour boundaries)
  + [Persona Instructions] (if persona selected)
  + [Activated Skills] (injected when specific tools are used)
  + [Conversation History]
  + [User Message]
```

### Base System Prompt (always included)
- Role definition: "You are a compliance information assistant for regulated industries"
- Core rules: search before answering, never fabricate citations, information not advice
- Response format: structured citations, confidence indicators
- British English requirement
- Pre-1963 labelling requirement

### Skills Pattern
When the agent calls a legislation search tool → inject "Legal Research" skill:
- How to cite UK legislation correctly
- Primary vs secondary legislation distinction
- Amendment status awareness

When the agent calls a case law search tool → inject "Case Law Analysis" skill:
- Neutral citation format
- Court hierarchy and precedent weight

Skills are configurable per tenant and can be associated with personas.

## Citation Verification (CRITICAL)

This is the most important quality gate. The Citation Verification Agent:
1. Receives the generated response with all inline citations
2. For EACH citation:
   - Calls Lex API `lookup_legislation` or `search_for_caselaw_by_reference` to verify the source exists
   - Compares the claim against the actual source text
   - Checks jurisdiction (e.g., not citing Scottish law for English housing)
   - Checks temporal validity (not citing repealed legislation as current)
3. Marks each citation: Verified / Unverified / Removed
4. If citations are removed, rewrites the affected sentence with uncertainty language
5. Emits `VerificationResultEvent` for the frontend

Target metrics:
- Citation verification pass rate: >95%
- Citations removed per response: <2%

## Confidence Scoring

| Level | Criteria |
|-------|----------|
| High | 3+ corroborating sources, all citations verified, well-established legal position |
| Medium | 1-2 sources, some citations unverified, or evolving regulation |
| Low | 0-1 sources, or significant uncertainty, or pre-1963 digitised content |

## Semantic Cache

Before calling the LLM:
1. Embed the user query
2. Search the cache collection for similar queries (cosine similarity > 0.95)
3. If cache hit: return cached response with `cache_hit: true` flag
4. If cache miss: proceed with full agent pipeline, store result in cache

Cache is tenant-scoped. TTL configurable per tenant (default 30 days).

## Testing Requirements
- Unit tests: Router correctly classifies query types
- Unit tests: Model routing selects correct tier
- Unit tests: Skills injection activates on correct tool calls
- Integration test: send question → Router → Orchestrator → Workers → Response with citations
- Integration test: citation verification catches fabricated section number
- Integration test: persona changes response tone
- Integration test: cancel mid-stream stops generation
- Integration test: semantic cache returns cached response
- Integration test: mandatory disclaimer present on every response
- Integration test: confidence indicator present and appropriate
- Test: multi-turn conversation maintains context
- Test: token usage accurately tracked per invocation

## Reference
- Functional Spec Sections: 3.1.x, 10.x, 16.x
- Tech Decisions: `docs/architecture/TECH_DECISIONS.md` §6 (SSE), §7 (Model Routing), §8 (Lex)
