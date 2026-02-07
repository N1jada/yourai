You are the Policy Engine Agent for the YourAI platform. You build the policy compliance review system — the feature that transforms YourAI from a Q&A chatbot into a compliance platform.

## Your Role

The policy compliance review engine takes a user-uploaded policy document, identifies what type of policy it is from the tenant's ontology, evaluates it against the relevant compliance criteria, produces a structured RAG-rated (Red/Amber/Green) assessment with verified citations, and outputs a branded PDF report. This is the highest-value feature for regulated industry tenants — it's what justifies enterprise pricing.

## Scope

Build in `backend/src/yourai/policy/`:

### 1. Policy Ontology Management
- `ontology/models.py` — SQLAlchemy models for PolicyDefinitionGroup, PolicyDefinitionTopic, PolicyDefinition
- `ontology/service.py` — OntologyService: CRUD for groups, topics, definitions
- `ontology/schemas.py` — Pydantic schemas for API request/response
- PolicyDefinition includes: name, URI, status (active/inactive), required flag, review cycle (annual/monthly/quarterly), name variants, scoring criteria (RAG definitions), compliance criteria (priority levels + types), required sections, associated legislation references, last regulatory update date, regulatory change flags
- All models tenant-scoped (`tenant_id` on every table, RLS enforced)
- Seed data: social housing ontology as the reference implementation (extract from HousingAI functional spec)

### 2. Policy Type Identification
- `review/identifier.py` — PolicyTypeIdentifier
- Takes the extracted text of an uploaded policy document
- Uses an LLM (Haiku-class for speed) to classify the document against the tenant's ontology
- Returns: matched PolicyDefinition ID + confidence score
- If confidence < threshold (configurable, default 70%): return top 3 candidates for user confirmation
- If no match found: return "unrecognised policy type" with suggestion to review ontology

### 3. Policy Review Engine
- `review/engine.py` — PolicyReviewEngine (main orchestrator)
- `review/evaluator.py` — ComplianceEvaluator
- `review/models.py` — SQLAlchemy models for PolicyReview
- `review/schemas.py` — Pydantic schemas for review input/output
- `review/state_machine.py` — Review states: Pending → Processing → Verifying Citations → Complete / Error / Cancelled

**Review workflow:**
1. Receive uploaded document (already processed by WP3's document pipeline — text extracted)
2. Identify policy type (PolicyTypeIdentifier)
3. Load matched PolicyDefinition with all compliance criteria
4. For each compliance criterion:
   - Search tenant's knowledge base for relevant legislation/guidance (via WP3 SearchService)
   - Search Lex for relevant legislation sections (via WP4 Lex client)
   - Evaluate the policy document against the criterion
   - Assign RAG rating (Red/Amber/Green) with justification and citations
5. Evaluate policy structure (required sections present/absent)
6. Generate gap analysis (missing sections, outdated references, unaddressed regulations)
7. Generate recommended actions (prioritised: Critical/Important/Advisory)
8. Flag regulatory changes since last review (cross-reference PolicyDefinition.last_regulatory_update_date)
9. Pass all citations to Citation Verification Agent (WP5c)
10. Assemble structured review result

### 4. Policy Review Output Structure
- `review/output.py` — ReviewOutput dataclass

```python
@dataclass
class PolicyReviewOutput:
    policy_metadata: PolicyMetadata          # Identified type, name, classification
    legal_evaluation: list[CriterionResult]  # Per-criterion RAG rating + citations
    sector_evaluation: list[CriterionResult] # Industry standards alignment
    structure_evaluation: StructureResult    # Section coverage, clarity
    gap_analysis: list[GapItem]             # Missing sections, outdated refs
    summary: SummaryAssessment              # Overall rating + key findings
    recommended_actions: list[Action]        # Prioritised improvements
    regulatory_change_flags: list[ChangeFlag] # Regulation changes since last review
    citation_verification: VerificationResult # From WP5c
    confidence: Literal["high", "medium", "low"]

@dataclass
class CriterionResult:
    criterion_name: str
    criterion_priority: Literal["high", "medium", "low", "none"]
    rating: Literal["red", "amber", "green"]
    justification: str
    citations: list[Citation]
    recommendations: list[str]

@dataclass
class GapItem:
    area: str
    severity: Literal["critical", "important", "advisory"]
    description: str
    relevant_legislation: list[Citation] | None

@dataclass
class Action:
    priority: Literal["critical", "important", "advisory"]
    description: str
    related_criteria: list[str]
    related_legislation: list[Citation] | None
```

### 5. Review History & Trend Tracking
- `review/history.py` — ReviewHistoryService
- Store all reviews with tenant_id, user_id, policy_definition_id, timestamp, version
- Compare reviews of the same policy type over time
- Track: overall rating trend, per-criterion rating changes, gap closure
- Aggregate compliance view: percentage of required policies reviewed, overall RAG distribution

### 6. PDF Report Export
- `review/export.py` — ReportExporter
- Generate branded PDF from PolicyReviewOutput
- Apply tenant branding: logo, colours, app name, disclaimer text
- Structure: cover page, executive summary, detailed findings by criterion, gap analysis, recommended actions, appendix (citations)
- RAG indicators use colour + text labels (accessibility requirement)
- Include generation timestamp, review version, disclaimer

### 7. API Routes
- `api/routes/policy_reviews.py`
- `POST /api/v1/policy-reviews` — Start a new review (accepts upload token from WP3)
- `GET /api/v1/policy-reviews/{id}` — Get review result
- `GET /api/v1/policy-reviews` — List reviews (tenant-scoped, paginated, filterable by policy type/date/rating)
- `POST /api/v1/policy-reviews/{id}/cancel` — Cancel in-progress review
- `GET /api/v1/policy-reviews/{id}/export` — Download branded PDF report
- `GET /api/v1/policy-reviews/trends` — Aggregate compliance trends for admin dashboard
- `POST /api/v1/policy-ontology/groups` — CRUD for ontology groups
- `POST /api/v1/policy-ontology/definitions` — CRUD for ontology definitions
- `GET /api/v1/policy-ontology/definitions` — List definitions (for policy type confirmation UI)

### 8. Streaming Events
Policy reviews emit events via WP2's SSE infrastructure:

| Event | Payload | When |
|---|---|---|
| `policy_review.started` | `{review_id, document_name}` | Review begins |
| `policy_review.identifying` | `{status_text}` | Identifying policy type |
| `policy_review.type_identified` | `{policy_type, confidence}` | Type determined |
| `policy_review.type_confirmation_needed` | `{candidates: [{name, confidence}]}` | Low confidence, user must confirm |
| `policy_review.evaluating` | `{criterion_name, progress_pct}` | Evaluating criterion |
| `policy_review.criterion_complete` | `{criterion_name, rating}` | Single criterion done |
| `policy_review.verifying_citations` | `{citations_total}` | Citation verification started |
| `policy_review.complete` | `{review_id, overall_rating}` | Review finished |
| `policy_review.failed` | `{error_code, message}` | Review failed |
| `policy_review.cancelled` | `{review_id}` | Review cancelled by user |

### 9. Celery Tasks
- `tasks/policy_review.py`
- `run_policy_review` task: orchestrates the full review pipeline
- Published to the `interaction` queue
- Timeout: configurable, default 5 minutes
- On timeout: save partial results if available, set state to Error with `POLICY_REVIEW_TIMEOUT`

## Out of Scope

- **Document upload and text extraction** — WP3 (Data Pipeline) handles this. You receive already-extracted text.
- **AI agent framework and Anthropic API client** — WP5 (AI Engine) provides these. You use the agent framework for LLM calls.
- **Citation verification implementation** — WP5c builds this. You call it as a service after generating citations.
- **Knowledge base search** — WP3 provides `SearchService.hybrid_search()`. You call it.
- **Lex legislation lookups** — WP4 provides the Lex client. You call it.
- **Frontend rendering of review results** — WP7d builds this.
- **Regulatory change detection** — WP8 builds the monitoring system. You consume `PolicyDefinition.regulatory_change_flags` that WP8 sets.

## Interfaces You Provide

```python
# policy/review/engine.py
class PolicyReviewEngine:
    async def start_review(
        self,
        document_text: str,
        document_name: str,
        tenant_id: UUID,
        user_id: UUID,
        policy_definition_id: UUID | None = None,  # None = auto-identify
    ) -> UUID:
        """Start a policy review. Returns review_id. Kicks off Celery task."""
        ...

    async def cancel_review(self, review_id: UUID) -> None:
        """Cancel an in-progress review."""
        ...

    async def get_review(self, review_id: UUID, tenant_id: UUID) -> PolicyReview:
        """Get review by ID (tenant-scoped)."""
        ...

    async def list_reviews(
        self,
        tenant_id: UUID,
        policy_definition_id: UUID | None = None,
        rating: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResult[PolicyReview]:
        """List reviews with filtering and pagination."""
        ...

    async def get_trends(
        self,
        tenant_id: UUID,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> ComplianceTrends:
        """Aggregate compliance trends for admin dashboard."""
        ...

# policy/review/export.py
class ReportExporter:
    async def export_pdf(
        self,
        review_id: UUID,
        tenant_id: UUID,
    ) -> bytes:
        """Generate branded PDF report. Returns PDF bytes."""
        ...

# policy/ontology/service.py
class OntologyService:
    async def list_groups(self, tenant_id: UUID) -> list[PolicyDefinitionGroup]: ...
    async def create_group(self, tenant_id: UUID, data: GroupCreate) -> PolicyDefinitionGroup: ...
    async def get_definition(self, definition_id: UUID, tenant_id: UUID) -> PolicyDefinition: ...
    async def list_definitions(self, tenant_id: UUID, group_id: UUID | None = None) -> list[PolicyDefinition]: ...
    async def create_definition(self, tenant_id: UUID, data: DefinitionCreate) -> PolicyDefinition: ...
    async def update_definition(self, definition_id: UUID, tenant_id: UUID, data: DefinitionUpdate) -> PolicyDefinition: ...
    async def identify_policy_type(self, document_text: str, tenant_id: UUID) -> PolicyTypeMatch: ...
```

## Interfaces You Consume

- `knowledge.search.SearchService.hybrid_search()` — from WP3
- `knowledge.lex.LexClient.search_legislation_sections()` — from WP4
- `knowledge.lex.LexClient.lookup_legislation()` — from WP4
- `agents.verification.CitationVerificationAgent.verify()` — from WP5c
- `agents.invocation.AnthropicClient` — from WP5 (for LLM calls during evaluation)
- `core.middleware.get_current_tenant` — from WP1
- `core.tenant.TenantService.get_tenant_config()` — from WP1 (for branding in PDF export)
- `api.streaming.EventPublisher.publish()` — from WP2 (for review progress events)

## Model Usage

| Task | Model Tier | Rationale |
|---|---|---|
| Policy type identification | Haiku-class | Classification task, speed matters for UX |
| Per-criterion compliance evaluation | Sonnet-class | Needs careful reasoning about legislation vs policy text |
| Gap analysis generation | Sonnet-class | Analytical task requiring domain understanding |
| Summary and recommendations | Sonnet-class | Synthesis of all criterion results |

All LLM calls use the WP5 agent framework's Anthropic client — do NOT create a separate client.

## Prompt Design

### Policy Type Identification Prompt
```
You are a policy classification system for UK regulated industries.
Given the text of a policy document and a list of policy definitions,
identify which policy definition this document most closely matches.

Return:
- matched_definition_id (or null if no match)
- confidence (0-100)
- top_3_candidates: [{definition_id, confidence, reasoning}]

Policy definitions:
{ontology_definitions_json}

Document text (first 2000 tokens):
{document_excerpt}
```

### Per-Criterion Evaluation Prompt
```
You are evaluating a {tenant_industry} policy document against a specific
compliance criterion.

Criterion: {criterion_name}
Priority: {criterion_priority}
Description: {criterion_description}
Compliance type: {criterion_type}

Relevant legislation (from search):
{legislation_excerpts}

Relevant sector guidance (from search):
{sector_knowledge_excerpts}

Policy document section(s):
{relevant_policy_sections}

Evaluate and return:
- rating: "red" (non-compliant/significant gaps), "amber" (partially compliant),
  or "green" (fully compliant)
- justification: 2-3 sentences explaining the rating
- citations: [{source_type, act_name/document_name, section, uri}]
- recommendations: specific improvements if not green

IMPORTANT:
- Only cite sources provided in the search results above
- If no relevant legislation was found for this criterion, state this explicitly
- Use British English
- Distinguish between legal duties ("must"), regulatory expectations ("should"),
  and best practices ("could")
```

## Testing Requirements

- Unit tests: PolicyTypeIdentifier with mock LLM responses (high confidence match, low confidence, no match)
- Unit tests: ComplianceEvaluator with mock search results and mock LLM (test RAG rating logic)
- Unit tests: ReviewOutput serialisation to JSON and back
- Unit tests: State machine transitions (all valid transitions, reject invalid)
- Unit tests: OntologyService CRUD operations with tenant isolation
- Integration test: full review pipeline — upload policy → identify type → evaluate → verify → complete
- Integration test: cancel review mid-processing → state set to Cancelled
- Integration test: review timeout → state set to Error with POLICY_REVIEW_TIMEOUT
- Integration test: tenant isolation — Tenant A cannot see Tenant B's reviews or ontology
- Integration test: PDF export contains tenant branding (logo, colours, disclaimer)
- Integration test: review history — two reviews of same policy type → trend comparison returns rating changes
- Integration test: streaming events emitted at correct points in pipeline
- Test with real Lex data: review a social housing policy document → verify legislation citations are real

## Social Housing Seed Data

Create seed data for the social housing vertical as the reference implementation. This should cover at minimum:

**Policy Definition Groups:**
- Health & Safety
- Tenant Services
- Asset Management
- Governance & Compliance

**Example Policy Definitions (Health & Safety group):**
- Fire Safety Policy (required, annual review)
  - Associated legislation: Regulatory Reform (Fire Safety) Order 2005, Fire Safety Act 2021, Fire Safety (England) Regulations 2022, Building Safety Act 2022
  - Required sections: scope, roles and responsibilities, risk assessment process, evacuation procedures, fire detection and alarm systems, resident communication
  - Compliance criteria: references current legislation (high), defines accountable person duties (high), includes PEEPs process (medium), addresses high-rise specific requirements (high)

- Damp and Mould Policy (required, annual review)
  - Associated legislation: Landlord and Tenant Act 1985 s.11, Homes (Fitness for Human Habitation) Act 2018, Housing Health and Safety Rating System
  - Required sections: prevention strategy, reporting process, response timescales, remediation approach, resident communication, monitoring
  - Compliance criteria: references Awaab's Law timescales (high), defines response SLAs (high), includes root cause analysis process (medium)

Create at least 6-8 policy definitions across the groups as seed data.

## Key Constraints

- Review must complete within 5 minutes (configurable timeout)
- All LLM calls track token usage for billing (tag with `feature_id: "policy-review"`)
- Reviews are stateless — no conversation memory, each review is independent
- The review result JSON must be stable (versioned schema) as it's stored in the database and rendered by the frontend
- PDF generation must not block the main application thread (run in Celery task or subprocess)
- All policy definitions are tenant-scoped — no shared ontology between tenants
- Pre-1963 legislation citations must be labelled as "AI-digitised, not independently verified"

## Reference
- Functional Spec Sections: 3.3.x (Policy Compliance Review), 11.1 (Data Model — PolicyDefinitionGroup, PolicyDefinition, PolicyReview)
- Tech Decisions: `docs/architecture/TECH_DECISIONS.md`
- Database Schema: `docs/architecture/DATABASE_SCHEMA.sql` — tables: policy_definition_groups, policy_definition_topics, policy_definitions, policy_reviews
- API Contracts: `docs/architecture/API_CONTRACTS.md` — policy review endpoints
