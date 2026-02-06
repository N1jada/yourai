# YourAI â€” Functional Specification (v2)

> **Purpose**: This document describes WHAT the system does, not HOW it is built. It is intended for a product owner to hand to a technical team before any architecture or technology decisions have been made. It should contain enough detail for a technical team to design and build an equivalent system from scratch.
>
> **Lineage**: This specification is adapted from the HousingAI platform (a UK social housing AI assistant). YourAI generalises HousingAI into a white-label, multi-tenant SaaS platform configurable for any regulated industry.
>
> **Version**: 2.0 â€” Incorporates findings from competitive analysis, multi-agent architecture research, MCP integration review, i.AI ecosystem assessment, and RAG pipeline best practices.

---

## 1. Product Overview

**YourAI** is a white-label, AI-powered knowledge assistant and policy compliance platform designed for regulated industries. It enables professionals to query a curated knowledge base of legislation, case law, regulatory standards, and industry guidance through a conversational AI interface. It also provides automated policy document compliance reviews and proactive regulatory change monitoring.

The platform is built on the Anthropic API (Claude) and uses a multi-agent orchestration architecture with a dedicated citation verification layer. Each tenant (customer organisation) receives a fully branded, configurable instance tailored to their industry vertical. The system ingests, processes, and indexes domain-specific documents, then makes them searchable through hybrid search (combining semantic vector search with keyword matching). An AI assistant uses these documents to provide grounded, cited answers to user queries.

UK legislation and case law are sourced from the **Lex API** â€” an open-source UK legal data platform built by the UK Government's Incubator for AI (i.AI) â€” self-hosted for production reliability, with the public hosted service available as a fallback.

### 1.1 White-Label & Multi-Tenancy

Each tenant deployment is configurable along the following dimensions:

| Dimension | What Is Configured |
|---|---|
| **Branding** | Logo, colour scheme, application name, favicon, email templates, custom domain, error pages, AI disclaimers, PDF export templates |
| **Industry Vertical** | Determines which legislation categories, regulatory bodies, compliance ontologies, and conversation templates are active |
| **Knowledge Base Scope** | Which legislation types, regulatory standards, and external sources are enabled |
| **AI Personas** | Industry-specific persona templates (e.g., compliance lead, customer experience lead) |
| **Policy Ontology** | The compliance definitions, scoring criteria, and required sections for that industry |
| **External Integrations** | Which external data sources (regulators, ombudsman services, government consultations, parliamentary data) are connected |
| **Subscription Tier** | Credit limits, user caps, feature gates, model routing preferences |
| **AI Behaviour Boundaries** | Mandatory disclaimers, confidence display thresholds, topic restrictions |

### 1.2 Target Industry Verticals (Initial)

While the platform is industry-agnostic by design, the following verticals are prioritised for launch:

- **Social Housing** (reference implementation, based on HousingAI)
- **Local Government & Public Sector**
- **Construction & Building Safety**
- **Planning & Property Development**
- **Social Care**
- **Healthcare (NHS & Private)**
- **Education**
- **Financial Services & Insurance**

### 1.3 Design Principles

These principles guide all feature decisions:

1. **Grounded, never fabricated**: Every factual claim must trace to a source document. The system must refuse rather than guess.
2. **Information, not advice**: The platform provides regulatory information and compliance analysis, never legal, financial, or medical advice.
3. **Transparent uncertainty**: When evidence is thin or ambiguous, the system must say so explicitly, with confidence indicators.
4. **Tenant isolation by default**: No architectural shortcut may compromise data separation between tenants.
5. **Accessible to all**: The interface must be usable by professionals with disabilities, meeting WCAG 2.2 AA.
6. **Auditable**: Every AI decision, every document access, every compliance rating must be traceable for regulatory purposes.
7. **British English throughout**: All AI-generated text, UI copy, and system messages use British English spelling and conventions.

---

## 2. User Roles & Personas

### 2.1 User Types

| Role | Description |
|---|---|
| **Regular User** | A professional who uses the AI assistant and knowledge base |
| **Administrator** | Has access to the admin dashboard, user management, persona configuration, guardrail management, and analytics |
| **Super Admin** | Created via system setup; has all permissions within a tenant |
| **Platform Admin** | YourAI platform operator; manages tenants, billing, and platform-wide configuration (not visible to tenants) |

### 2.2 User Statuses

| Status | Meaning |
|---|---|
| Pending | Account created but not yet active |
| Active | Fully operational account |
| Disabled | Account suspended by administrator |
| Deleted | Account permanently removed (triggers data erasure cascade â€” see Section 19) |

### 2.3 Job Roles (User Profile)

Each tenant configures a list of job roles relevant to their industry. Users select their job role from this tenant-specific list. A default set is provided per industry vertical and can be customised.

**Example defaults by vertical:**

| Vertical | Default Job Roles |
|---|---|
| Social Housing | Housing Officer, Property Manager, Maintenance Manager, Tenant Liaison Officer, Administrator, Director, Other |
| Financial Services | Compliance Officer, Risk Manager, Financial Adviser, Operations Manager, Director, Other |
| Local Government | Planning Officer, Housing Officer, Environmental Health Officer, Social Worker, Legal Officer, Director, Other |
| Construction | Building Safety Manager, Principal Designer, Principal Contractor, Accountable Person, Site Manager, Director, Other |
| Education | Head Teacher, Safeguarding Lead, SENCO, Governance Professional, MAT Executive, Other |

### 2.4 Permissions

The system uses role-based access control. Permissions include:

**User Management**: list users, view user, create user, delete user, update user role, update user profile, update user preferences, update user job role

**Role Management**: list user roles, delete user roles

**Persona Management**: list personas, create persona, update persona, delete persona

**Guardrail Management**: list guardrails, view guardrail, create guardrail, update guardrail, delete guardrail

**Dashboard & Analytics**: show dashboard, show user management, query account usage stats

**Activity**: list activity logs, export activity logs

**Knowledge Base Management**: create knowledge base, delete knowledge base, sync knowledge base, upload documents, delete documents

**Compliance Management**: view regulatory alerts, manage policy review schedule, export compliance reports

**Tenant Configuration** (Platform Admin only): create tenant, update tenant settings, manage tenant billing, configure industry vertical

**Operations**: cancel conversation, cancel policy review

---

## 3. Core Features

### 3.1 AI Conversational Assistant

#### 3.1.1 Conversation Management

- Users can create new conversations
- Conversations persist and are listed in a sidebar for quick access
- Conversation titles are auto-generated from the first user message
- Users can rename conversations manually
- Users can delete conversations (triggers data erasure â€” see Section 19)
- Each conversation belongs to a single user (private)
- Conversations have a state machine: Pending â†’ Waiting for Reply â†’ Generating Reply â†’ Outputting Reply â†’ Ready
- Conversations can be exported as PDF or Markdown (with tenant branding on PDFs)

#### 3.1.2 Messaging

- Users type messages in a chat input field
- Messages support file attachments (uploaded documents)
- Messages are streamed back in real-time (token by token) from the AI
- Each message tracks its state: Pending, Success, Error, Cancelled
- Messages have roles: User or Assistant
- Users can cancel an in-flight request (stops AI generation)
- Token usage (input/output/total) is displayed per conversation
- Users can provide feedback on AI responses (thumbs up/down with optional comment)
- Message feedback is stored for quality improvement and analytics

#### 3.1.3 Conversation Templates

Each tenant can configure conversation templates â€” pre-built query starting points relevant to their industry:

**Example templates (Social Housing):**
- "Review our obligations under the Building Safety Act 2022"
- "What are the current RSH consumer standards requirements for [topic]?"
- "Summarise recent Housing Ombudsman decisions on [topic]"

**Example templates (Construction):**
- "What are the golden thread requirements for this building type?"
- "Explain the Accountable Person duties under BSA 2022"
- "What CDM 2015 obligations apply to [role]?"

Templates appear as clickable suggestions when a user creates a new conversation.

#### 3.1.4 Agent Modes

The AI assistant operates in two modes:

**Conversation Mode** (default):
- Multi-turn conversational Q&A about the tenant's domain topics
- Maintains conversation history across messages (session persistence)
- Searches across ALL knowledge base categories when answering questions
- Provides cited answers with references to specific legislation sections, case law, and policies
- Supports persona-based behaviour adaptation
- All responses pass through the Citation Verification Agent before delivery (see Section 10)

**Policy Review Mode**:
- Stateless (no conversation memory)
- User uploads a policy document
- AI evaluates the document against the tenant's policy definitions ontology
- Returns structured compliance assessment with RAG (Red/Amber/Green) ratings
- No persona adaptation
- All citations in the review are independently verified

#### 3.1.5 AI Personas

Administrators can create custom AI personas that alter the assistant's behaviour and tone. Users select a persona before sending a message.

Each tenant receives a set of default persona templates based on their industry vertical. Administrators can modify these or create entirely new personas.

**Example persona perspectives (Social Housing):**
- **Asset & Compliance Lead**: Focus on regulatory compliance, legal obligations, risk mitigation
- **Customer Experience Lead**: Focus on tenant satisfaction, communication, complaint resolution
- **Strategy & Transformation Lead**: Focus on strategic implications, organisational change, innovation
- **Sustainability & Retrofit Lead**: Focus on environmental sustainability, energy efficiency, carbon reduction
- **Customer Persona**: Accessible language for residents, practical impacts

**Example persona perspectives (Financial Services):**
- **Regulatory Compliance Lead**: Focus on FCA/PRA requirements, regulatory reporting
- **Risk Management Lead**: Focus on risk assessment, controls, and mitigation
- **Customer Outcomes Lead**: Focus on consumer duty, fair treatment, vulnerable customers

**Example persona perspectives (Local Government):**
- **Planning Policy Lead**: Focus on NPPF compliance, local plan policies, development management
- **Housing & Homelessness Lead**: Focus on housing duties, homelessness reduction, allocations
- **Environmental Health Lead**: Focus on public health, licensing, environmental regulation

Each persona has:
- Name
- Description
- System instructions (that modify the AI's behaviour)
- Activated skills context (automatic context injection when specific tools are used â€” see Section 16.4)

#### 3.1.6 Message Metadata & Citations

AI responses include structured metadata that the UI renders as collapsible sections:

- **Legal Sources**: References to specific legislation (Act name, section number, URI, link to legislation.gov.uk), each with a verification status (Verified / Unverified / Pre-1963 Digitised)
- **Legal Annotations**: Expert commentary on legislation/case law (content + contributor attribution)
- **Company Policy Sources**: References to the organisation's internal policies (document name, section, page reference)
- **Case Law Sources**: Court decisions cited (case name, neutral citation, court, date, relevant paragraph numbers)
- **Parliamentary Sources**: Hansard debate references, Written Questions, committee findings (where Parliament MCP is enabled)
- **Confidence Indicator**: Overall response confidence level (High / Medium / Low) based on source coverage

#### 3.1.7 AI Behaviour Rules

The AI assistant MUST:
- Search the knowledge base before answering any factual or citation-dependent question
- Never fabricate citations, legal references, case names, or section numbers
- Distinguish between legal duties ("must"), regulatory expectations ("should"), and best practices ("could")
- Provide status updates during analysis (visible to user as commentary)
- Cite specific Act names, section numbers, and case references
- Honestly report when knowledge base gaps exist
- Include a mandatory disclaimer appropriate to the tenant's industry vertical (see Section 3.1.8)
- Display a confidence indicator on every response
- Use British English spelling and conventions throughout
- Label any information sourced from LLM-transcribed historical legislation (pre-1963) as "AI-digitised, not independently verified"

The AI assistant MUST NOT:
- Provide legal, financial, or medical advice (only information)
- Include information not found in search results when answering factual questions
- Answer citation requests without first searching
- Present low-confidence findings without explicit uncertainty language
- Cross tenant data boundaries under any circumstances
- Generate content that could constitute regulated advice in the tenant's industry

#### 3.1.8 Mandatory Disclaimers

Each tenant configures an industry-appropriate disclaimer that appears on every AI response. Default disclaimers per vertical:

| Vertical | Default Disclaimer |
|---|---|
| Social Housing | "This is AI-generated information based on UK housing legislation and guidance. It does not constitute legal advice. Always consult a qualified legal professional for advice specific to your situation." |
| Financial Services | "This is AI-generated regulatory information. It does not constitute financial advice or a personal recommendation. Consult your compliance team or a qualified adviser." |
| Healthcare | "This is AI-generated information based on healthcare regulations and guidance. It does not constitute medical or clinical advice. Follow your organisation's clinical governance processes." |
| Local Government | "This is AI-generated information based on UK legislation and government guidance. It does not constitute legal advice. Consult your authority's legal team for binding interpretations." |

#### 3.1.9 Confidence Scoring

Every AI response receives a confidence classification based on source coverage:

| Level | Criteria | Display Behaviour |
|---|---|---|
| **High** | Multiple corroborating sources found; citations verified; well-established legal position | Green indicator; no additional caveat |
| **Medium** | Some relevant sources found but incomplete coverage; or area of evolving regulation | Amber indicator; "This area may have limited coverage in our knowledge base" |
| **Low** | Few or no relevant sources found; or significant uncertainty in interpretation | Red indicator; "Limited sources available â€” verify this information independently" |

The confidence level is determined by the Citation Verification Agent (Section 10) based on: number of corroborating sources, recency of sources, whether citations were independently verified, and whether the question falls within the tenant's configured knowledge domain.

#### 3.1.10 Real-Time Streaming

During AI response generation, the following typed events are streamed to the frontend in real-time:

| Event Type | Payload | Purpose |
|---|---|---|
| `agent_start` | `{agent_name, task_description}` | Sub-agent beginning work |
| `agent_progress` | `{agent_name, status_text}` | Agent thinking/processing commentary |
| `agent_complete` | `{agent_name, duration_ms}` | Sub-agent finished |
| `content_delta` | `{text}` | Partial response text as generated |
| `legal_source` | `{act_name, section, uri, verification_status}` | Legislation reference discovered |
| `case_law_source` | `{case_name, citation, court, date}` | Case law reference discovered |
| `annotation` | `{content, contributor, type}` | Expert commentary found |
| `company_policy_source` | `{document_name, section}` | Internal policy reference |
| `parliamentary_source` | `{type, reference, date, member}` | Parliamentary data reference |
| `confidence_update` | `{level, reason}` | Confidence assessment updated |
| `usage_metrics` | `{model, input_tokens, output_tokens}` | Token counts per model call |
| `verification_result` | `{citations_checked, citations_verified, issues}` | Citation verification outcome |
| `error` | `{code, message, recoverable}` | Error during processing |

The frontend must render an acknowledgement within 1 second of a user message ("Analysing your question about..."), progress indicators as sub-agents start and complete, and partial results as they become available.

### 3.2 Knowledge Base

#### 3.2.1 Knowledge Base Categories

The system manages multiple knowledge bases organised by category:

| Category | Description | Data Source |
|---|---|---|
| **Legislation** | Acts of Parliament, Statutory Instruments, Regulations | Lex API (self-hosted, Section 4) |
| **Case Law** | Court decisions and precedents | Lex API (self-hosted, Section 4) |
| **Explanatory Notes** | Government explanatory notes on legislation | Lex API (self-hosted, Section 4) |
| **Amendments** | Legislative amendment records | Lex API (self-hosted, Section 4) |
| **Company Policy** | Organisation-specific internal policies uploaded by users | Uploaded (Section 5) |
| **Sector Knowledge** | Industry best practices and guidance from relevant professional bodies | Uploaded (Section 5) |
| **Parliamentary** | Hansard debates, Written Questions, committee transcripts | Parliament MCP (optional, Section 4.7) |

Each tenant can enable or disable categories and configure which legislation types and court jurisdictions are relevant to their industry.

#### 3.2.2 Document Upload (Company Policies & Sector Knowledge)

Users can upload documents to the company policy and sector knowledge bases:
- **Supported formats**: PDF, DOCX, TXT
- **Maximum file size**: 50MB per document
- **Upload mechanism**: File picker or drag-and-drop
- **Processing pipeline**: After upload, documents go through automatic processing (see Section 5)
- **Organisation**: Documents are organised in a hierarchical folder structure
- **Operations**: Browse, view metadata (name, size, type, processing status, chunk count, last indexed), delete files/folders
- **Bulk operations**: Delete multiple documents by path prefix
- **Version tracking**: When a document with the same name is re-uploaded, the previous version is retained and the new version is indexed. Users can view version history and revert.

#### 3.2.3 Document Processing Status

Each uploaded document progresses through states:
1. Uploaded
2. Validating (format check, virus scan, size check)
3. Extracting Text (Pending â†’ Processing â†’ Complete/Failed)
4. Chunking (Pending â†’ Processing â†’ Complete/Failed)
5. Contextualising (prepending chunk context â€” see Section 5.3.1)
6. Embedding (Pending â†’ Processing â†’ Complete/Failed)
7. Indexing (adding to search index)
8. Ready (searchable)

Failed state includes: error code, human-readable error message, retry count, next retry time.

Users can see the processing status of their uploaded documents in real-time.

#### 3.2.4 Hybrid Search

The knowledge base supports hybrid search combining semantic and keyword-based retrieval:

**Stage 1 â€” Broad Retrieval:**
- **Vector search**: User queries are converted to embeddings; similar document chunks are found using vector similarity search (returning top ~200 candidates)
- **Keyword search (BM25)**: The same query is run as a keyword search against a full-text index (returning top ~200 candidates)
- Results are filtered by knowledge base category and tenant

**Stage 2 â€” Fusion:**
- Results from vector and keyword search are merged using Reciprocal Rank Fusion (RRF), which combines rankings from both methods without requiring score normalisation

**Stage 3 â€” Reranking:**
- A cross-encoder reranking model scores each candidate against the original query
- Top 5â€“10 results are selected for inclusion in the AI prompt

A configurable similarity threshold controls minimum result quality (default: 40â€“50% for vector search). Results are paginated for UI display.

### 3.3 Policy Compliance Review

#### 3.3.1 Policy Review Workflow

1. User clicks "Policy Rating" button in the conversation interface
2. User uploads a policy document (PDF/DOCX/TXT)
3. System validates and processes the document
4. AI identifies the policy type from the tenant's ontology (or asks user to confirm if uncertain)
5. AI reviews the document against the matched policy definition's compliance criteria
6. Real-time status updates stream to the user during processing
7. Citation Verification Agent checks all legal references in the review
8. Results are displayed when complete
9. Users can cancel a review in progress
10. Users can export the review as a branded PDF report

#### 3.3.2 Policy Definitions Ontology

Each tenant maintains a structured ontology of policy definitions that serves as the compliance baseline. The ontology is configurable per industry vertical.

**Policy Definition Groups**: Top-level organisational groupings

**Policy Definition Topics**: Cross-cutting themes that can be associated with multiple definitions

**Policy Definitions** include:
- Name and description
- URI (unique identifier)
- Status (Active/Inactive)
- Whether the policy is required or optional
- Review cycle (Annual/Monthly/Quarterly)
- Name variants (alternative names for the same policy)
- Scoring criteria with RAG (Red/Amber/Green) definitions
- Compliance criteria with priority levels (High/Medium/Low/None) and types
- Required document sections
- Associated legislation (links to specific Acts/sections that the policy must address)
- Last regulatory update date (when the underlying regulation last changed)

#### 3.3.3 Policy Review Output

The AI produces a structured compliance assessment:

- **Policy Metadata**: Identified policy type, name, and classification
- **Legal/Regulatory Evaluation**: Compliance against specific legislation sections with RAG ratings and verified citations
- **Sector Best Practice Evaluation**: Alignment with industry standards
- **Policy Structure Evaluation**: Clarity, completeness, section coverage
- **Gap Analysis**: Missing sections, outdated references, areas where the policy does not address current regulation
- **Summary Assessment**: Overall compliance rating and key findings
- **Recommended Actions**: Prioritised list of improvements, categorised as Critical (Red), Important (Amber), and Advisory (Green)
- **Regulatory Change Flags**: Any areas where underlying regulation has changed since the policy was last reviewed (see Section 3.8)

RAG Scoring Levels:
- **Green**: Fully compliant
- **Amber**: Partially compliant / needs improvement
- **Red**: Non-compliant / significant gaps

#### 3.3.4 Policy Review States

- Pending â†’ Processing â†’ Verifying Citations â†’ Complete / Error / Cancelled

#### 3.3.5 Policy Review History

- All reviews are stored and accessible from the admin dashboard
- Reviews can be compared over time for the same policy type (trend tracking)
- Administrators can view aggregate compliance trends across their policy portfolio

### 3.4 Admin Dashboard

Accessible only to users with the "show dashboard" permission.

#### 3.4.1 Analytics Dashboard

**Statistics Cards:**
- Credit Usage (with progress bar showing limit per billing period, alerts at 70%/85%/95%)
- Conversations Started (count)
- Users Created (count)
- Policy Reviews Completed (count)
- Average Response Confidence (High/Medium/Low distribution)

**Time Series Charts:**
- Credit Usage over time
- New Conversations over time
- New Users over time
- Messages per Conversation over time
- Response Quality (user feedback thumbs up/down ratio)
- Confidence Distribution over time

**Date Range Filtering:**
- Presets: Current Billing Period, Last 7 Days, Last 30 Days
- Custom date range selection
- All charts and statistics respond to date range changes

**Knowledge Base Analytics:**
- Most queried topics (from conversation analysis)
- Knowledge gaps (queries that returned low-confidence results)
- Document usage (which documents are cited most frequently)

#### 3.4.2 User Management

- Search/filter users by name, email, or role
- View user table with columns: Status, User ID, Name, Email, Last Login, Roles, Conversations Count
- Status badges: Pending, Active, Inactive
- Actions per user: View analytics, Edit, Delete (with data erasure confirmation)
- Invite new users (creates account in identity provider)
- Assign/modify user roles
- Bulk invite via CSV upload

#### 3.4.3 Persona Management

- List all personas with name, description, and usage count
- Create new personas (name, description, system instructions, activated skills)
- Edit existing personas
- Delete personas with confirmation
- Duplicate existing personas as templates

#### 3.4.4 Guardrail Management

- Configure AI safety guardrails
- CRUD operations on guardrails
- Guardrail statuses: Creating, Updating, Versioning, Ready, Failed, Deleting
- Test guardrails against sample queries before activation

#### 3.4.5 Activity Log

- View system activity audit log
- Activities are tagged as: User, System, Security, or AI
- Filter by tag, user, date range
- Export audit log as CSV (for regulatory compliance evidence)
- Retention period: configurable per tenant (default 7 years for regulated industries)

### 3.5 News Feed

- The home dashboard displays a news feed with industry-relevant news
- News sources are configurable per tenant (RSS/Atom feed URLs)
- News stories have: title, URL, snippet, source attribution, image, publish date
- Stories are fetched from configured RSS/Atom feeds
- "Refresh News" button to fetch latest articles
- Display layout: masonry grid (responsive columns)

### 3.6 Canvas Workspace

- Users can open AI responses in an expandable canvas view
- Canvas features:
  - Title editing
  - Rich text editing
  - Markdown and HTML content rendering
  - Save/load functionality
  - Auto-save
  - Export as PDF (with tenant branding) or Markdown

### 3.7 User Profile

Users can manage their profile:
- View/edit first name and last name
- Select job role from predefined (tenant-configured) list
- View email address (read-only, from identity provider)
- View avatar (Gravatar-based)
- Notification preferences (email alerts for regulatory changes, credit warnings)
- Sign out
- Request data export (GDPR Subject Access Request â€” see Section 19)
- Request account deletion (GDPR Right to Erasure â€” see Section 19)

### 3.8 Regulatory Change Monitoring

The system proactively monitors for regulatory changes that affect tenants and their policies.

#### 3.8.1 Change Detection

- The system periodically checks for updates to legislation and regulatory standards relevant to each tenant's industry vertical
- For tenants using self-hosted Lex, weekly Parquet dataset updates are compared against the previous version to identify new or amended legislation
- For configured external regulatory sources (RSH, FCA, CQC, etc.), periodic polling detects new publications, consultations, and standard changes

#### 3.8.2 Impact Assessment

When a regulatory change is detected:
1. The system identifies which policy definitions in the tenant's ontology are affected (by matching legislation references)
2. An AI agent generates a brief impact summary: what changed, which policies are affected, and what action may be required
3. Affected policy definitions are flagged with a "Regulatory Change" indicator showing the date and nature of the change

#### 3.8.3 Notification

- Administrators receive an in-app notification and optional email alert
- The admin dashboard shows a "Regulatory Changes" panel with pending items
- Each change can be: Acknowledged, Dismissed, or actioned (triggers a policy re-review)

#### 3.8.4 Compliance Calendar

- Administrators can view a calendar showing:
  - Upcoming policy review dates (based on review cycles in the ontology)
  - Recent regulatory changes awaiting acknowledgement
  - Scheduled government consultations closing dates
- Calendar entries link to relevant policy definitions and review tools

### 3.9 User Feedback & Quality Loop

- Users can rate AI responses with thumbs up/down
- Optional free-text comment on ratings
- Administrators can view feedback analytics: satisfaction rate over time, most common complaints, lowest-rated topics
- Feedback data is used to identify knowledge base gaps and persona improvements
- Low-rated responses are flagged for internal quality review

### 3.10 Conversation Export & Reporting

- Individual conversations can be exported as branded PDF or Markdown
- Policy review results can be exported as branded PDF reports
- Administrators can generate aggregate compliance reports across their policy portfolio
- Reports include: compliance trends over time, gap analysis summary, regulatory change impact summary
- Scheduled report generation (weekly/monthly) with email delivery

---

## 4. UK Legislation & Case Law via Lex API

YourAI replaces the custom legislation crawler from HousingAI with the **Lex API** (`https://github.com/i-dot-ai/lex`), an open-source UK legal API built by the UK Government's Incubator for AI (i.AI). This provides a significantly richer, pre-indexed dataset with semantic search built in, eliminating the need for YourAI to crawl, parse, chunk, and embed legislation itself.

### 4.1 What Lex Provides

Lex is a comprehensive UK legal data platform offering:

| Dataset | Coverage |
|---|---|
| **Legislation** | 219,655+ Acts and Statutory Instruments (1267â€“present, complete from 1963) |
| **Case Law** | 69,910+ court judgments (2001â€“present) |
| **Case Summaries** | 61,107+ AI-generated case summaries |
| **Amendments** | 892,210+ legislative amendments |
| **Explanatory Notes** | 83,350+ explanatory note sections |
| **PDF Digitisation** | Historical legislation digitised using AI (pre-1963) |

Data is sourced from legislation.gov.uk under the Open Government Licence v3.0 and The National Archives under the Open Justice Licence.

### 4.2 Deployment Strategy: Self-Hosted Primary, Public Fallback

The public Lex API at `lex.lab.i.ai.gov.uk` carries an explicit warning: *"This API is hosted as an experimental service and should not be used as a production dependency."* YourAI therefore **self-hosts the Lex stack** as the primary production deployment, with the public hosted service available as a fallback only.

**Self-hosted Lex (primary):**
- Full control over rate limits, uptime, and data freshness
- No dependency on external government service availability
- Data sovereignty for tenants requiring it
- Customisable tool definitions and response formatting
- Weekly dataset updates via Parquet bulk downloads (automated)

**Public Lex API (fallback):**
- Used only when self-hosted instance is unavailable
- Rate limited: 60 requests/minute, 1,000 requests/hour per IP
- Health checked continuously; traffic routed to fallback automatically on failure

### 4.3 Hybrid MCP + Direct API Architecture

Lex exposes its capabilities through both a Model Context Protocol (MCP) server and a REST API. YourAI uses both, depending on the use case:

**MCP (for interactive agent tool calls):**
- Used when the AI agent needs to dynamically discover and select which legislation tools to use during a conversation
- The agent decides in real-time whether to search for legislation, look up a specific Act, retrieve explanatory notes, or search amendments
- This is the natural interaction mode for the Conversation Agent

**Direct REST API (for deterministic operations):**
- Used for known, predictable operations: specific legislation lookups by URI, full-text retrieval, background data synchronisation, regulatory change detection
- Lower latency (no MCP protocol overhead or LLM tool-selection reasoning)
- Used by the Regulatory Change Monitoring system (Section 3.8)

### 4.4 Available MCP Tools

The Lex MCP server exposes 19 tools across five categories:

**Legislation Tools:**
| Tool | Purpose |
|---|---|
| `search_for_legislation_acts` | Semantic search for Acts and Statutory Instruments by topic |
| `search_for_legislation_sections` | Semantic search for individual sections of legislation |
| `lookup_legislation` | Look up a specific Act or SI by title/reference |
| `get_legislation_sections` | Retrieve all sections of a specific Act |
| `get_legislation_full_text` | Retrieve the full text of a specific piece of legislation |
| `proxy_legislation_data` | Proxy requests to legislation.gov.uk for raw data |

**Case Law Tools:**
| Tool | Purpose |
|---|---|
| `search_for_caselaw` | Semantic search for court judgments |
| `search_for_caselaw_section` | Search within specific sections of judgments |
| `search_for_caselaw_by_reference` | Look up cases by neutral citation reference |
| `search_caselaw_by_reference` | Alternative reference-based case lookup |
| `search_caselaw_summaries` | Search AI-generated case summaries |
| `proxy_caselaw_data` | Proxy requests for raw case law data |

**Explanatory Notes Tools:**
| Tool | Purpose |
|---|---|
| `search_explanatory_note` | Search explanatory notes by topic |
| `get_explanatory_note_by_legislation` | Get explanatory notes for a specific Act |
| `get_explanatory_note_by_section` | Get explanatory notes for a specific section |

**Amendment Tools:**
| Tool | Purpose |
|---|---|
| `search_amendments` | Search for legislative amendments |
| `search_amendment_sections` | Search for amendments to specific sections |

**Utility Tools:**
| Tool | Purpose |
|---|---|
| `get_live_stats_api_stats_get` | Retrieve API statistics |
| `health_check_healthcheck_get` | Check API health |

Tools are loaded on-demand rather than all at once, to minimise per-request token overhead (each tool definition consumes LLM context tokens).

### 4.5 What This Replaces

The following HousingAI components are **no longer needed** and are removed from YourAI:

| Removed Component | Replaced By |
|---|---|
| UK Legislation Crawler service | Lex API `search_for_legislation_*` and `lookup_legislation` tools |
| Legislation XML parsing and text extraction | Lex API `get_legislation_full_text` and `get_legislation_sections` tools |
| Legislation chunking and embedding pipeline | Lex's built-in Qdrant-powered semantic search |
| Legislation vector store maintenance | Lex API handles indexing and updates |
| Case law JSON parsing | Lex API `search_for_caselaw*` tools |
| Rate-limited crawler (3,000 req/5-min) | Self-hosted Lex (unlimited) or public API (60/min, 1,000/hr) |
| Document catalogs for legislation | Lex bulk downloads (Parquet format, weekly updates) |
| Hourly knowledge base sync for legislation | Lex dataset updated independently; weekly sync for change detection |

### 4.6 What Remains (Document Processing for Uploaded Content)

The document processing pipeline (Section 5) is still required for:
- **Company Policy** documents uploaded by users (PDF, DOCX, TXT)
- **Sector Knowledge** documents uploaded by users
- Any other tenant-uploaded content that is not legislation or case law

### 4.7 Parliament MCP (Optional External Data Source)

YourAI can optionally integrate with the **Parliament MCP** server (`https://github.com/i-dot-ai/parliament-mcp`), another i.AI open-source project, to provide access to UK parliamentary data:

| Tool | Purpose |
|---|---|
| `search_members` | Search MPs/Lords with postcode lookup |
| `get_election_results` | Election results for constituencies |
| `search_parliamentary_questions` | Search Written Questions with semantic search |
| `search_contributions` | Search Hansard debate transcripts |
| `find_relevant_contributors` | Find MPs who have spoken on a topic |
| Committee tools | Search committee memberships, publications, and inquiries |

**Value for tenants:** Provides legislative context beyond the text of the law â€” what was said during debate, what questions have been asked about specific regulations, which committees are examining relevant topics. Particularly valuable for local government, planning, and social housing tenants.

**Deployment:** Self-hosted alongside Lex (same tech stack: FastMCP, Qdrant, Azure OpenAI embeddings). Daily automated ingestion of new parliamentary data.

### 4.8 Important Caveats

- LLM-transcribed historical legislation (pre-1963) is not independently verified; responses using this data must be labelled accordingly in the UI ("AI-digitised, not independently verified")
- Lex provides legal information, not legal advice; YourAI must maintain this distinction in all AI responses and disclaimers
- Data is sourced under Open Government Licence v3.0 and Open Justice Licence; attribution requirements must be met in all outputs

---

## 5. Document Processing Pipeline (Uploaded Content)

This section describes the automated pipeline that processes user-uploaded documents from raw source to searchable knowledge base entries. This pipeline applies to Company Policy and Sector Knowledge documents only; legislation and case law are handled by Lex (Section 4).

### 5.1 Document Ingestion Sources

#### 5.1.1 User Uploads

Users upload documents (PDF, DOCX, TXT) via the web interface, which enter the processing pipeline.

#### 5.1.2 Document Catalogs (Optional)

The system supports configurable "document catalogs" for bulk ingestion of sector-specific content (e.g., regulatory body publications, industry guidance documents). Catalogs can be configured per tenant.

### 5.2 Text Extraction

Raw documents are converted to plain text using format-appropriate strategies:

| Input Format | Extraction Strategy |
|---|---|
| PDF (scanned) | OCR-based text extraction with layout analysis |
| PDF (text-based) | Direct text extraction preserving structure |
| DOCX | Structured text extraction preserving headings, lists, and tables |
| Plain text (TXT, MD, CSV) | Pass-through |

Table content is extracted and preserved as structured text (not discarded). Headers, footers, and page numbers are identified and separated from body content.

### 5.3 Chunking

Extracted text is split into chunks suitable for embedding. The target chunk size is **256â€“512 tokens** (approximately 1,000â€“2,000 bytes), significantly smaller than the previous 5,000-byte default, based on research showing optimal recall at this range.

**Structure-aware chunking** (default for policy documents and sector knowledge):
1. Identify document structure (headings, sections, clauses, numbered items)
2. Split on structural boundaries (sections, clauses)
3. Respect clause and paragraph boundaries â€” never split mid-sentence
4. Preserve section numbering as chunk metadata
5. Build parent-child chunk hierarchy: Document â†’ Section â†’ Paragraph
6. Retrieval occurs at paragraph granularity, but parent section context can be included in the AI prompt for surrounding context

**Fixed-size chunking** (fallback for unstructured PDFs):
- 512-token sliding window with 10â€“20% overlap
- Overlap ensures important content at chunk boundaries is not lost

**AI-powered chunking** (higher quality, higher cost):
- An LLM intelligently identifies chunk boundaries based on content type
- Selects appropriate strategy based on content: header-aware, semantic, hybrid-recursive
- Reserved for high-value documents where accuracy is critical

#### 5.3.1 Contextual Chunk Enrichment

Before embedding, each chunk is enriched with contextual information following Anthropic's contextual retrieval pattern:

- A brief summary is prepended to each chunk describing where it fits in the overall document
- Example: "This chunk is from Section 4.2 of the Health & Safety Policy (2024), covering fire safety procedures for communal areas."
- The contextual prefix is generated by an LLM using the full document and the chunk as input
- This reduces retrieval failures by approximately 49% compared to embedding raw chunks

### 5.4 Embedding Generation

Each chunk is converted to a high-dimensional vector embedding:

- **Model**: Configurable per deployment (recommended: text-embedding-3-large or Voyage 3 Large for legal/compliance content)
- **Dimensions**: Model-dependent (e.g., 1,024 or 3,072 dimensions)
- **Embedding model abstraction**: An adapter layer allows changing embedding models without re-architecting
- **Versioning**: Each embedding is tagged with `{model_name}:{model_version}`. Embeddings from different models are never mixed in the same index.
- **Migration**: When an embedding model is upgraded, a background re-embedding job processes all existing chunks into a new index. The old index is retained until migration is verified, then deprecated.
- Batch processing with parallel execution

### 5.5 Full-Text Indexing

In addition to vector embeddings, all chunks are indexed in a full-text search engine (BM25) to support keyword-based retrieval:

- Exact matches on policy numbers, regulation codes, clause references
- Boolean search operators for precise queries
- Tenant-scoped indexes

### 5.6 Metadata Extraction

Automated metadata extraction enriches document records:
- Document title, author, creation date, last modified date
- Document type classification (policy, procedure, guidance, report)
- Key topics and themes (LLM-extracted)
- Referenced legislation (Act names, section numbers extracted from document text)

### 5.7 Processing Schedule

- Document processing runs every 15 seconds (picks up pending documents)
- Failed document retries run every minute with exponential backoff (1s â†’ 2s â†’ 4s, max 30s, with jitter)
- Documents that fail after 3 retries are moved to a dead letter queue with full diagnostic context
- Administrators can view and manually retry dead-lettered documents

---

## 6. External Knowledge Sources

Beyond the indexed knowledge base and Lex API, the AI agent can query additional external sources in real-time. These are configurable per tenant based on industry vertical.

### 6.1 Configurable External Source Types

| Source Type | Description | Example (Social Housing) |
|---|---|---|
| **Regulatory Standards** | Fetches current standards from sector regulators | Regulator of Social Housing (RSH) consumer and economic standards |
| **Government Consultations** | Fetches currently open government consultations | UK government consultations from gov.uk filtered by sector |
| **Ombudsman / Dispute Resolution** | Fetches determinations and reports from sector ombudsman services | Housing Ombudsman determinations on specific topics |
| **Professional Body Guidance** | Fetches guidance from industry professional bodies | CIH, NHF, HQN guidance documents |
| **Government Datasets** | Structured data from UK government open data sources | Housing statistics, planning application data, school performance data |

### 6.2 Specialist Sub-Agents

For complex external sources, dedicated sub-agents can be configured per tenant. A sub-agent specialises in a particular domain and provides:
- Domain-specific search and retrieval
- Contextual understanding of the source's structure
- Citation of specific case numbers, report references, and dates

**Example (Social Housing):** Housing Ombudsman Specialist sub-agent covering case findings, complaint procedures, Complaint Handling Code compliance, jurisdiction, and remedies.

**Example (Local Government):** Parliamentary Intelligence sub-agent combining Lex legislation data with Parliament MCP debate context and Written Questions for comprehensive legislative analysis.

### 6.3 Adding External Sources

New external sources are configured at the tenant level by defining:
- Source name and description
- API endpoint or data retrieval method
- Search parameters and filtering logic
- Response parsing and citation formatting
- Rate limits and caching policy
- Whether a dedicated sub-agent is required
- Error handling behaviour (fail silently, warn user, or block response)

### 6.4 UK Government Dataset Discovery

The platform maintains awareness of available UK government open datasets (informed by i.AI's curated dataset catalogue) to facilitate adding new data sources per vertical:

- Parliament (Hansard, votes, bills)
- Law (legislation, case law â€” via Lex)
- Economy (Companies House, Nomis labour market data)
- Geospatial (census, planning applications)
- Health (NHS datasets)
- Education (school performance, Ofsted reports)
- Crime (police statistics)

Each dataset has known licence information, update frequency, and format, enabling rapid assessment of integration feasibility.

---

## 7. Billing & Usage Tracking

### 7.1 Credit System

- AI model usage is tracked in credits
- Credits abstract the complexity of underlying token costs (input tokens, output tokens, and embedding tokens all have different prices per model)
- Each tenant has a credit limit per billing period (configurable per subscription tier)
- Usage is tracked per conversation/invocation
- Token counts (input + output) are recorded for each AI model call, tagged with `tenant_id`, `model_id`, and `feature_id`

### 7.2 Cost Control

- **Model routing**: Lightweight models (Haiku-class) are used for classification and routing; mid-tier models (Sonnet-class) for analysis; top-tier models (Opus-class) only for complex synthesis. This significantly reduces per-query cost.
- **Semantic caching**: Repeated or highly similar compliance queries are served from a response cache (keyed by semantic similarity, not exact match), with a configurable TTL and cache-hit indicator shown to users
- **Per-tenant budgets**: Soft warnings at 70%, 85%, 95% of credit allocation; hard cap at 100% (configurable: hard cap can be disabled for Enterprise tenants)
- **Per-conversation limits**: Optional per-conversation token budget to prevent runaway multi-agent chains

### 7.3 Billing Events

- **Credit**: Credits added to account (via subscription renewal or manual top-up)
- **Usage**: Credits consumed by AI usage (with breakdown: conversation, policy review, title generation, regulatory monitoring)
- **Adjustment**: Manual credit adjustments by Platform Admin

### 7.4 Usage Statistics

Administrators can view:
- Credit usage over time (with progress toward limit)
- Breakdown by feature (conversations vs. policy reviews vs. regulatory monitoring)
- Breakdown by model (cost per model tier)
- Breakdown by date range
- Per-conversation token usage
- Cost projections based on current usage trends

### 7.5 Subscription Tiers

The platform supports multiple subscription tiers per tenant:

| Tier | Credit Limit | Users | Features |
|---|---|---|---|
| **Starter** | Configurable | Up to N users | Core AI assistant, knowledge base, basic personas |
| **Professional** | Configurable | Up to N users | + Policy review, custom personas, guardrails, regulatory change monitoring, export/reporting |
| **Enterprise** | Configurable | Unlimited | + Custom integrations, dedicated support, self-hosted Lex, Parliament MCP, custom domains, SLA guarantees, priority model routing |

Specific limits and pricing are configured at the platform level.

---

## 8. Authentication & Authorisation

### 8.1 Authentication Flow

- Users authenticate via an external identity provider (OAuth2/OpenID Connect)
- PKCE (Proof Key for Code Exchange) flow for browser security
- JWT tokens for API authentication
- Silent token refresh in the background
- 12-hour session duration before re-authentication required
- Multi-factor authentication support (delegated to identity provider)

### 8.2 Service-to-Service Authentication

- Internal services authenticate via bearer tokens
- The AI engine receives a scoped auth token for each request
- Tokens have TTLs matching request timeout
- MCP connections to self-hosted Lex use internal service authentication (not exposed to internet)

### 8.3 Tenant Isolation

- All API requests are scoped to the authenticated user's tenant
- Data is logically isolated per tenant (tenant ID on all records)
- Database-level Row-Level Security (RLS) enforces tenant isolation as a defence-in-depth measure
- Vector database uses namespace-per-tenant isolation (documents embedded into tenant-specific namespaces at ingestion time; every search query includes tenant filter applied before similarity search, not after)
- Cross-tenant data access is impossible by design
- Database-per-tenant or schema-per-tenant available for Enterprise tenants requiring demonstrable physical separation

### 8.4 Error Handling

- 401 Unauthorised: Attempt silent token refresh, then redirect to login
- 403 Forbidden: Display permission denied notification
- 423 User Not Active: Display account inactive error page
- 404 Not Found: Display error page
- 429 Rate Limited: Display rate limit message with retry-after indication

---

## 9. Real-Time Communication

The system uses real-time push channels (WebSocket or Server-Sent Events) for live updates:

### 9.1 User Channels

Per-user channel broadcasting:
- Conversation title updated
- Conversation title updating (loading state)
- Policy review created
- Regulatory change alert (when regulatory monitoring detects a relevant change)
- Credit usage warning (at configured thresholds)

### 9.2 Conversation Channels

Per-conversation channel broadcasting:
- Agent started (`{agent_name, task_description}`)
- Agent progress (`{agent_name, status_text}`)
- Agent completed (`{agent_name, duration_ms}`)
- Content delta (`{text}`)
- Legal source discovered (`{act_name, section, uri, verification_status}`)
- Case law source discovered (`{case_name, citation, court, date}`)
- Company policy source discovered (`{document_name, section}`)
- Parliamentary source discovered (`{type, reference, date}`)
- Annotation discovered (`{content, contributor, type}`)
- Confidence updated (`{level, reason}`)
- Usage metrics (`{model, input_tokens, output_tokens}`)
- Verification result (`{citations_checked, citations_verified, issues}`)
- Message state updated
- Message completed
- Conversation cancelled
- Conversation state updated
- Error (`{code, message, recoverable}`)

### 9.3 Policy Review Channels

Per-review channel broadcasting:
- Status updated (progress commentary)
- Citation verification progress
- Completed
- Failed (`{error_code, message}`)

### 9.4 Knowledge Base Channels

Per-knowledge-base channel broadcasting:
- Document created (new document uploaded)
- Document processing state changed
- Document ready (processing complete)
- Document failed (processing failed, with error details)

---

## 10. Citation Verification & Hallucination Defence

This section describes the multi-layered approach to preventing hallucinated citations and ensuring response accuracy â€” the single most critical quality requirement for a regulated-industry compliance platform.

### 10.1 Citation Verification Agent

A dedicated Citation Verification Agent operates as a **mandatory post-processing step**, separate from the generation agent. This separation prevents the generation agent from being biased by citation pressure.

**Process:**
1. The primary agent generates a response with inline citations
2. The Citation Verification Agent receives the response and its cited sources
3. For each citation, the agent:
   - Confirms the cited Act/section/case exists (via Lex API lookup)
   - Confirms the cited content accurately represents the source (not misrepresented)
   - Checks for jurisdictional correctness (e.g., not citing Scottish legislation for an English housing query)
   - Checks for temporal correctness (e.g., not citing repealed legislation as current)
4. Citations are marked as: **Verified**, **Unverified** (source exists but claim could not be confirmed), or **Removed** (source does not exist or is materially misrepresented)
5. If any citations are removed, the affected portion of the response is rewritten or flagged
6. The verification result is included in the streaming events so the UI can display verification status per citation

### 10.2 Additional Hallucination Defences

| Layer | Mechanism |
|---|---|
| **Grounding requirement** | Agent system prompt mandates: "Only include information found in search results. If you cannot find relevant sources, say so." |
| **Search-before-answer** | The agent loop requires at least one knowledge base search before generating any factual claim |
| **Structured tool output** | Citations are returned as structured data (not free text), making verification deterministic |
| **Confidence scoring** | Low source coverage triggers explicit uncertainty language and a visible Low confidence indicator |
| **Refusal on thin evidence** | When fewer than 2 relevant sources are found, the agent states the limitation rather than speculating |
| **Pre-1963 labelling** | Historical legislation transcribed by AI is always labelled as such in the UI |
| **User feedback loop** | Thumbs-down responses are flagged for review, enabling detection of systematic hallucination patterns |
| **Automated evaluation** | Regular evaluation runs using faithfulness, relevance, and context precision metrics against test query sets (see Section 20.3) |

### 10.3 Hallucination Monitoring

The platform tracks hallucination-related metrics:
- Citation verification pass rate (target: >95%)
- Citations removed per response (target: <2% of total citations)
- User-reported inaccuracies (via feedback)
- Automated evaluation scores per knowledge domain

These metrics are visible to Platform Admins and inform prompt engineering improvements.

---

## 11. Data Model Summary

### 11.1 Core Entities

**Tenant**
- ID, name, slug
- Industry vertical
- Branding configuration (logo URL, colours, app name, favicon URL, custom domain, disclaimer text)
- Subscription tier, credit limit, billing period
- Active/inactive status
- Configured news feed URLs
- Configured external source integrations
- AI behaviour boundaries (confidence thresholds, topic restrictions)
- Vector namespace identifier

**User**
- ID, tenant ID, email, given name, family name
- Job role, status (active/pending/disabled/deleted)
- Last active timestamp
- Notification preferences
- Associated roles (many-to-many)
- Associated permissions (via roles)
- Data deletion request timestamp (if applicable)

**User Role**
- ID, tenant ID, name, description
- Associated permissions

**Conversation**
- ID, tenant ID, user ID, title, state
- Template ID (if started from template)
- Associated messages

**Message**
- ID, conversation ID, request ID
- Role (user/assistant), content, state
- Associated metadata (legal sources, annotations, company policy sources, parliamentary sources)
- File attachments
- Confidence level (High/Medium/Low)
- Verification result (citations checked, verified, removed)
- User feedback (thumbs up/down, comment)

**Agent Invocation**
- ID, conversation ID, request ID, user ID, tenant ID
- Mode (conversation/policy-review), query
- Persona ID, context ID
- State, attachments
- Model used, model tier (haiku/sonnet/opus)
- Associated events (streaming lifecycle events)
- Associated usage records
- Cache hit flag

**Knowledge Base**
- ID, tenant ID, name, category (legislation/company-policy/sector-knowledge/case-law/explanatory-notes/amendments/parliamentary)
- Source type (lex-api/uploaded/catalog/parliament-mcp)
- Associated documents (for uploaded content only)

**Document** (uploaded content only)
- ID, knowledge base ID, tenant ID, name
- Document URI (unique identifier)
- Source URI, MIME type, byte size, hash
- Processing state (uploaded through ready, or failed)
- Text extraction strategy and output
- Chunking strategy and results
- Version number, previous version ID
- Metadata (title, author, creation date, document type, extracted topics, referenced legislation)
- Retry count, last error message, dead letter flag

**Document Chunk** (uploaded content only)
- ID, document ID, chunk index
- Parent chunk ID (for hierarchical chunking)
- Language, source URI
- Byte range (start/end/size), hash
- Contextual prefix (generated summary)
- Vector embedding
- Embedding model name and version
- Full-text index entry (for BM25 search)

**Document Annotation**
- Associated with a document URI
- Type (expert commentary, etc.)
- Content and contributor

**Persona**
- ID, tenant ID, name, description, system instructions
- Activated skills (context injection rules)
- Usage count

**Guardrail**
- ID, tenant ID, name, description, status
- Configuration rules

**Conversation Template**
- ID, tenant ID, name, prompt text, category
- Industry vertical association

**Policy Definition Group**
- ID, tenant ID, name, description
- Contains policy definitions

**Policy Definition Topic**
- ID, tenant ID, name
- Many-to-many with policy definitions

**Policy Definition**
- ID, tenant ID, name, URI, status (active/inactive)
- Group, description, required flag
- Review cycle (annual/monthly/quarterly)
- Name variants, scoring criteria, compliance criteria, required sections
- Associated legislation references (Act names, section numbers)
- Last regulatory update date
- Regulatory change flags (pending changes awaiting acknowledgement)

**Policy Review**
- ID, request ID, user ID, tenant ID
- State (pending/processing/verifying/complete/error/cancelled)
- Result (structured JSON), source
- Citation verification result
- Version (for tracking re-reviews of the same policy)

**Regulatory Change Alert**
- ID, tenant ID
- Change type (new legislation, amendment, new regulatory standard, consultation)
- Source reference (Lex URI, external source URL)
- Summary (AI-generated impact description)
- Affected policy definition IDs
- Status (pending/acknowledged/dismissed/actioned)
- Detected date, acknowledged date, actioned date

**News Story**
- ID, tenant ID, title, URL, snippet, source, image URL
- Published date, fetched date

**Canvas**
- ID, tenant ID, user ID, title, content, HTML content
- Save state tracking

**Activity Log**
- ID, tenant ID, timestamp, user ID, action, detail
- Tags (user/system/security/ai)
- Retention expiry date

**Billing Event**
- Tenant ID, type (credit/usage/adjustment)
- Amount, timestamp, associated invocation
- Model ID, feature ID (conversation/policy-review/title-generation/regulatory-monitoring)

**Semantic Cache Entry**
- ID, tenant ID
- Query embedding, response, sources
- TTL, created timestamp, hit count

**User Feedback**
- ID, message ID, user ID, tenant ID
- Rating (up/down), comment
- Timestamp
- Review status (pending/reviewed/actioned)

### 11.2 Key Relationships

```
Tenant --< User --< Conversation --< Message
Tenant --< KnowledgeBase --< Document --< DocumentChunk
User --< UserRole >-- Role >-- Permission
Conversation --< AgentInvocation --< AgentInvocationEvent
Document --< DocumentAnnotation
Tenant --< PolicyDefinitionGroup --< PolicyDefinition >-- PolicyDefinitionTopic
PolicyDefinition --< RegulatoryChangeAlert
User --< PolicyReview
AgentInvocation --< BillingEvent
Tenant --< Persona
Tenant --< Guardrail
Tenant --< ConversationTemplate
Tenant --< NewsStory
Tenant --< ActivityLog
Tenant --< RegulatoryChangeAlert
Tenant --< SemanticCacheEntry
Message --< UserFeedback
```

---

## 12. Background Processing

### 12.1 Queue-Based Jobs

The system uses background job queues for:

**Document Processing (uploaded content only):**
- File validation (format, virus scan, size)
- Text extraction from uploaded documents
- Chunking extracted text
- Contextual enrichment (generating chunk context prefixes)
- Generating vector embeddings (parallelised batch processing)
- Full-text indexing (BM25)
- Metadata extraction

**Knowledge Base Operations:**
- Syncing knowledge bases from document catalogs (where configured)
- Retrying failed document processing (with exponential backoff)
- Embedding model migration (re-embedding existing chunks when model is upgraded)

**Lex Data Operations:**
- Weekly Parquet dataset download and diff (for regulatory change detection)
- Lex self-hosted instance data refresh

**Interaction Processing:**
- AI agent invocations (sending messages to AI engine via Anthropic API)
- Citation verification (post-processing)
- Conversation title generation
- Billing event recording

**Regulatory Monitoring:**
- External regulatory source polling (configurable per tenant)
- Change detection and impact assessment
- Alert generation and notification

**Reporting:**
- Scheduled report generation (weekly/monthly compliance reports)
- Report delivery via email

**Queue Names:**
- Default queue
- Knowledge base ingest queue
- Document catalog ingest queue
- Interaction queue
- Verification queue
- Regulatory monitoring queue
- Reporting queue

### 12.2 Scheduled Tasks

| Schedule | Task |
|---|---|
| Every 15 seconds | Process pending documents in knowledge base |
| Every minute | Retry failed document processing (exponential backoff) |
| Every hour | Poll external regulatory sources for changes |
| Daily | Parliament MCP data ingestion (if enabled) |
| Weekly (Sunday 03:00 UTC) | Download Lex Parquet updates and run change detection |
| As configured per tenant | Generate and deliver scheduled compliance reports |

### 12.3 Dead Letter Queue

Documents and jobs that fail after the maximum retry count (default: 3) are moved to a dead letter queue:
- Full diagnostic context is captured (error message, stack trace, input data hash)
- Administrators can view dead-lettered items in the admin dashboard
- Manual retry, skip, or delete actions are available
- Dead letter items older than 30 days are automatically purged (configurable)

---

## 13. File Attachment Handling

### 13.1 Upload Flow

1. User selects file in the UI
2. File is validated client-side (format, size)
3. File is uploaded and an upload token is returned
4. Upload token is submitted with the message or policy review request
5. Backend validates the file (virus scan, format verification, size check)
6. File is downloaded and converted to the appropriate format

### 13.2 Supported Formats

- **Documents**: PDF, DOC, DOCX (rendered as document blocks for AI)
- **Images**: PNG, JPG, JPEG, GIF, WEBP (rendered as image blocks for AI)
- **Text**: TXT, MD, CSV (rendered as text blocks for AI)

### 13.3 Size Limits

- Maximum file size per upload: 50MB
- Maximum total attachments per message: 10 files or 100MB (whichever is reached first)

### 13.4 Temporary URLs

File attachments use time-limited signed URLs for secure access during processing. URLs expire after 1 hour.

---

## 14. Error Handling

### 14.1 Error Pages

The application handles these error states:
- **User Not Active**: Account is not active, contact support
- **Not Found**: Page does not exist
- **General Error**: Unexpected error, try again later
- **Rate Limited**: Too many requests, try again in [N] seconds
- **Service Unavailable**: Platform undergoing maintenance

All error pages display tenant branding.

### 14.2 AI-Specific Error Taxonomy

| Error Code | Condition | User-Facing Message | Recovery Action |
|---|---|---|---|
| `AI_LOW_CONFIDENCE` | Fewer than 2 relevant sources found | "I found limited information on this topic. The answer below should be verified independently." | Response delivered with Low confidence indicator |
| `AI_NO_SOURCES` | Zero relevant sources found | "I couldn't find relevant information in the knowledge base for this query. Try rephrasing or check if the topic is within our covered areas." | No response generated; suggestions offered |
| `AI_VERIFICATION_FAILED` | Citation verification found fabricated sources | "Some references in this response could not be verified and have been removed. The remaining information is grounded in verified sources." | Response delivered with removed citations flagged |
| `AI_CREDIT_EXCEEDED` | Tenant credit allocation exhausted | "Your organisation's AI credit allocation has been reached for this billing period. Contact your administrator." | Response not generated; admin notified |
| `AI_CREDIT_EXCEEDED_MID` | Credits exhausted during multi-agent processing | "Processing was interrupted because your credit allocation was reached. A partial response is available below." | Partial response delivered |
| `LEX_UNAVAILABLE` | Both self-hosted and fallback Lex unreachable | "UK legislation search is temporarily unavailable. I can still answer using your organisation's policy documents and sector knowledge." | Response generated without legislation sources; flagged |
| `DOCUMENT_PROCESSING_FAILED` | Document could not be processed after retries | "This document could not be processed. It may be corrupted, password-protected, or in an unsupported format." | Document moved to dead letter queue; admin can retry |
| `POLICY_REVIEW_TIMEOUT` | Policy review exceeded time limit | "The policy review took longer than expected and was stopped. This may happen with very large documents. Try splitting the document or contact support." | Review cancelled |

### 14.3 Error Monitoring

- All errors are logged with: timestamp, tenant ID, user ID, error code, error message, stack trace, request ID
- Application errors are tracked via external monitoring with alerting
- Error rates per tenant are tracked and anomalies trigger alerts

---

## 15. Help & Support

The application includes a comprehensive help section with:

1. **Getting Started**: Creating first conversation, navigating the interface
2. **Working with Conversations**: Conversation modes, using templates, managing conversations, understanding responses, confidence indicators, citation verification
3. **Knowledge Base**: Accessing, uploading documents, document processing, using documents in conversations
4. **Policy Reviews**: Running a review, understanding RAG ratings, exporting reports, tracking improvements
5. **Regulatory Monitoring**: Understanding alerts, compliance calendar, acknowledging changes
6. **Profile & Settings**: Managing profile, notification preferences, account security
7. **Tips & Best Practices**: Getting better results, efficient conversation management, working with the knowledge base
8. **Troubleshooting**: Common issues, document upload issues, getting help
9. **Accessibility**: Keyboard shortcuts, screen reader guidance, accessibility statement
10. **Contact Support**: Email link to support team, in-app feedback mechanism

Help content is tenant-customisable to reflect industry-specific terminology and workflows.

---

## 16. AI Engine: Anthropic API Integration

### 16.1 Model Provider

YourAI uses the **Anthropic API** directly (not AWS Bedrock) as the sole LLM provider:
- Model: Claude (latest available via Anthropic API)
- Authentication: Anthropic API key per tenant or platform-level
- Streaming: Server-Sent Events for real-time response delivery

### 16.2 Model Routing

Different model tiers are used for different tasks to optimise cost and latency:

| Task | Model Tier | Rationale |
|---|---|---|
| Query classification and routing | Haiku-class (fastest, cheapest) | Simple classification doesn't need large models |
| Conversation title generation | Haiku-class | Lightweight task |
| Knowledge base search query formulation | Haiku-class | Query rewriting is a focused task |
| Contextual chunk enrichment | Haiku-class | Generating chunk context prefixes during ingestion |
| Primary conversation analysis | Sonnet-class | Good balance of quality and cost for most queries |
| Policy review analysis | Sonnet-class | Structured analysis benefits from capable model |
| Citation verification | Sonnet-class | Verification requires careful reasoning |
| Complex multi-source synthesis | Opus-class (optional) | Only for queries requiring deep cross-referencing across many sources |
| Regulatory change impact assessment | Sonnet-class | Analytical task requiring domain understanding |

Tenants on the Enterprise tier can configure model routing preferences (e.g., default to Opus-class for all analysis).

### 16.3 Multi-Agent Architecture

The AI engine uses multi-agent orchestration following a **Router â†’ Orchestrator-Workers â†’ Evaluator** pattern:

**Router Agent** (Haiku-class):
- Classifies incoming query by type (factual question, policy interpretation, compliance check, general discussion)
- Determines which tools and sub-agents are needed
- Routes to appropriate orchestration path

**Primary Orchestrator Agent** (Sonnet-class, Conversation Mode):
- Receives user message + conversation history + persona instructions
- Delegates to parallel specialist workers as needed
- Has access to tools: knowledge base search, Lex API (via MCP), external source queries
- Synthesises findings from workers into a coherent response with inline citations
- Orchestrates sub-agents for complex queries (e.g., cross-referencing legislation with case law and ombudsman decisions)

**Knowledge Workers** (parallel, Sonnet-class):
- **Policy Retrieval Worker**: Searches tenant's uploaded policy documents
- **Legislation Worker**: Queries Lex for relevant Acts and sections
- **Case Law Worker**: Queries Lex for relevant court decisions
- **External Source Worker**: Queries configured external sources (regulatory standards, ombudsman, consultations)
- **Parliamentary Worker**: Queries Parliament MCP (if enabled)

**Policy Review Agent** (Sonnet-class):
- Receives uploaded document
- Identifies policy type from tenant's ontology
- Evaluates against compliance criteria
- Returns structured compliance assessment with RAG ratings

**Citation Verification Agent** (Sonnet-class):
- Mandatory post-processing step (see Section 10)
- Verifies every citation in the response independently
- Marks citations as Verified / Unverified / Removed

**Quality Assurance Agent** (Sonnet-class):
- Reviews output for completeness, clarity, relevance, professionalism
- Checks mandatory disclaimer is present
- Checks confidence indicator is appropriate
- Currently in testing mode (auto-accepts all responses)

**Title Generation Agent** (Haiku-class):
- Generates conversation titles from first message

**Specialist Sub-Agents** (configurable per tenant):
- Domain-specific agents for complex external sources
- Each has tailored system instructions and tool access

### 16.4 Skills Pattern (Context Injection)

Inspired by the Lex MCP's "skills" system, YourAI implements automatic context injection when specific tools are activated:

- When the agent invokes a legislation search tool, a "Legal Research" skill is injected into the system prompt, providing guidance on citing UK legislation correctly, distinguishing between primary and secondary legislation, and noting amendment status
- When the agent invokes a case law search tool, a "Case Law Analysis" skill is injected, providing guidance on neutral citation format, court hierarchy, and precedent weight
- When the agent invokes the Housing Ombudsman tool, a "Complaint Handling" skill is injected, providing domain-specific context
- Skills are configurable per tenant and can be associated with personas

This pattern ensures the agent receives relevant domain guidance exactly when it needs it, without bloating the base system prompt.

### 16.5 Tool Integration

The AI agent has access to the following tool categories:

| Tool Category | Source | Purpose | Connection Method |
|---|---|---|---|
| Knowledge Base Search (Vector) | Internal vector store | Semantic search of uploaded company policies and sector knowledge | Direct API |
| Knowledge Base Search (BM25) | Internal full-text index | Keyword search of uploaded content | Direct API |
| Legislation Search | Self-hosted Lex | Search UK Acts, SIs, and sections | MCP (interactive) / REST (deterministic) |
| Case Law Search | Self-hosted Lex | Search court judgments and summaries | MCP (interactive) / REST (deterministic) |
| Explanatory Notes | Self-hosted Lex | Retrieve legislative explanatory notes | MCP (interactive) / REST (deterministic) |
| Amendment Search | Self-hosted Lex | Search legislative amendments | MCP (interactive) / REST (deterministic) |
| Parliamentary Search | Self-hosted Parliament MCP | Search Hansard, Written Questions, committees | MCP (interactive) |
| Regulatory Standards | Configurable external API | Fetch current regulatory standards | Direct API |
| Government Consultations | Configurable external API | Fetch open consultations | Direct API |
| Ombudsman/Dispute Reports | Configurable external API | Fetch ombudsman determinations | Direct API |
| Semantic Cache | Internal cache | Check for cached responses to similar queries | Direct API |

---

## 17. Non-Functional Requirements

### 17.1 Performance Targets

| Metric | Target | Measurement |
|---|---|---|
| API response time (non-AI endpoints) | < 200ms (p95) | Server-side latency |
| AI chat first token latency | < 2 seconds | Time from user message to first streamed token |
| AI chat full response | < 15 seconds (typical), < 30 seconds (complex multi-agent) | Time from user message to completion |
| Document processing throughput | â‰¥ 100 documents/hour per tenant | Pipeline processing rate |
| Search latency (hybrid) | < 500ms | Time from query to ranked results |
| Page load time | < 3 seconds | Time to interactive |

### 17.2 Availability & Reliability

| Metric | Target |
|---|---|
| Platform uptime | 99.9% (excluding planned maintenance) |
| Recovery Point Objective (RPO) | < 1 hour (database), < 24 hours (vector indexes) |
| Recovery Time Objective (RTO) | < 4 hours |
| Planned maintenance windows | Weekdays 02:00â€“06:00 UTC, communicated 48 hours in advance |

### 17.3 Scalability

- **Multi-tenancy**: All data and configuration is isolated per tenant
- **Horizontal scalability**: The platform must support multiple concurrent tenants without performance degradation
- **Concurrent users**: Support at least 100 concurrent users per tenant, 1,000 platform-wide
- **Background processing**: Job queues must scale independently of the web application

### 17.4 Security

- **Rate limiting**: External API calls (including Lex) must respect source API rate limits; internal API endpoints rate-limited per tenant
- **Data encryption**: At rest (AES-256) and in transit (TLS 1.2+)
- **Secret management**: API keys, database credentials, and encryption keys stored in a dedicated secrets manager (not in application code or environment variables in plain text)
- **Penetration testing**: Annual third-party penetration test
- **Dependency scanning**: Automated vulnerability scanning of all dependencies in CI/CD

### 17.5 Data Management

- **Session persistence**: Conversation history must persist across sessions
- **User isolation**: Users can only see their own conversations
- **Permission-based access**: Features are gated by role-based permissions
- **Audit logging**: System activities are logged with user/system/security/ai tags per tenant
- **Credit tracking**: AI usage is tracked against a configurable credit limit per billing period per tenant
- **Object storage**: Documents and processed artifacts are stored in object storage (not database)
- **Vector search**: Semantic search uses vector embeddings with configurable similarity thresholds (for uploaded content)
- **Backup**: Automated daily database backups with 30-day retention; weekly full backups with 90-day retention

### 17.6 Operational

- **Real-time streaming**: AI responses must stream to the user in real-time, not wait for complete generation
- **Retry handling**: Failed document processing must retry automatically with exponential backoff
- **Cancellation support**: Users can cancel in-flight AI requests and policy reviews
- **Error monitoring**: Application errors are tracked via external monitoring with alerting
- **Background processing**: Long-running tasks (document processing, crawling) run asynchronously
- **White-label branding**: Each tenant's instance must be fully brandable (including custom domains, email templates, PDF reports, error pages, and AI disclaimers)
- **British English**: All system-generated text, UI copy, and AI responses use British English spelling and conventions

### 17.7 Compliance & Certifications

| Certification | Priority | Timeline | Notes |
|---|---|---|---|
| **Cyber Essentials Plus** | Mandatory (UK public sector) | Pre-launch | Required for UK government procurement |
| **ISO 27001** | High | Within 12 months | Required/expected by financial services, healthcare, and education tenants |
| **SOC 2 Type II** | Medium | Within 18 months | International credibility |
| **GDPR compliance** | Mandatory | Pre-launch | See Section 19 |

---

## 18. Migration Path from HousingAI

For organisations currently using HousingAI, the migration path to YourAI is:

1. **Tenant creation**: Create a tenant with the "Social Housing" industry vertical
2. **Configuration migration**: Import existing personas, guardrails, and policy ontology
3. **Knowledge base migration**: Upload existing company policy and sector knowledge documents (legislation and case law are now served by Lex)
4. **User migration**: Migrate user accounts and role assignments
5. **Conversation history**: Optionally migrate conversation history (conversations re-indexed with tenant ID)
6. **Branding**: Apply existing HousingAI branding to the new tenant
7. **Verification**: Run a parallel period where both systems are available to users
8. **Cutover**: Redirect HousingAI domain to YourAI tenant

---

## 19. Data Privacy & GDPR Compliance

### 19.1 Data Processing Principles

- YourAI acts as a **Data Processor** on behalf of each tenant (the Data Controller)
- Data Processing Agreements (DPAs) are established per tenant
- Personal data is processed only for the purposes specified by the tenant
- Data minimisation: only data necessary for the service is collected and retained

### 19.2 Right to Erasure (Cascade)

When a user requests deletion (or an administrator deletes a user), the following data erasure cascade is executed:

| Data Type | Erasure Action | Timeline |
|---|---|---|
| User profile | Hard delete from database | Immediate |
| Conversations & messages | Hard delete from database | Immediate |
| Vector embeddings of user-uploaded documents | Re-index knowledge base without deleted user's private documents; update vector store | Within 24 hours |
| Cached AI responses involving user data | Invalidate and purge from semantic cache | Immediate |
| Audit log entries | Anonymise (replace user ID with "DELETED_USER") but retain entry for regulatory compliance | Immediate |
| File attachments | Delete from object storage | Within 24 hours |
| Billing records | Anonymise (remove user identification) but retain for accounting compliance | Immediate |

### 19.3 Subject Access Requests (SAR)

Users can request an export of all their personal data:
- Conversations and messages (as JSON or PDF)
- User profile information
- Policy review history
- Feedback submitted
- Activity log entries related to their account

Export is generated as a ZIP file and made available for download via a time-limited signed URL.

### 19.4 Data Retention

| Data Type | Default Retention | Configurable |
|---|---|---|
| Conversations | 3 years | Yes (per tenant) |
| Policy reviews | 7 years | Yes (per tenant) |
| Audit logs | 7 years | Yes (per tenant, minimum 1 year) |
| Document processing artifacts | Until document deleted | N/A |
| Billing records | 7 years | No (regulatory requirement) |
| Semantic cache | 30 days TTL | Yes (per tenant) |
| Dead letter queue items | 30 days | Yes |

### 19.5 Data Residency

- Default deployment: UK data centres
- All tenant data (database, object storage, vector store) resides within the configured region
- Self-hosted Lex instance deployed in the same region as the platform
- No data is transferred to Anthropic beyond the AI prompt content sent via API calls (Anthropic's data retention policy applies: zero-day retention on API by default)

---

## 20. Accessibility

### 20.1 WCAG 2.2 AA Compliance

The platform must meet WCAG 2.2 Level AA accessibility standards. Key requirements for the AI chat interface:

| Requirement | Implementation |
|---|---|
| Chat container role | `role="log"` with `aria-label="Conversation"` |
| New messages | `aria-live="polite"` announcements for new assistant messages |
| Streaming completion | "Response complete" notification for screen readers when streaming finishes |
| Focus management | Visible focus indicators meeting 3:1 contrast ratio |
| Keyboard operability | All interactions operable via keyboard (send message, cancel, navigate conversations, provide feedback) |
| Colour contrast | All text meets 4.5:1 contrast ratio (normal text) or 3:1 (large text) |
| RAG indicators | Red/Amber/Green compliance ratings have text labels in addition to colour (not colour-only) |
| Confidence indicators | High/Medium/Low indicators use text + icon, not colour alone |
| Motion | Respect `prefers-reduced-motion` for streaming animations |
| Document upload | Drag-and-drop has equivalent keyboard/button alternative |
| Error messages | Associated with form fields via `aria-describedby` |

### 20.2 Accessibility Statement

Each tenant instance includes a public accessibility statement conforming to the UK Public Sector Bodies (Websites and Mobile Applications) Accessibility Regulations 2018.

---

## 21. Observability & Monitoring

### 21.1 Distributed Tracing

- OpenTelemetry tracing across all services (web application, AI engine, document processing, Lex API, external sources)
- Each user request generates a trace ID that propagates through all agent calls, tool invocations, and background jobs
- Trace data enables end-to-end latency analysis per agent, per tool, per tenant

### 21.2 LLM-Specific Observability

- Every LLM API call is logged with: model, input tokens, output tokens, latency, tenant ID, feature ID, cache hit status
- Agent decision paths are logged: which tools were called, in what order, what results were returned, what was synthesised
- Prompt versions are tracked: system prompts, persona instructions, and skill injections are versioned and logged per invocation
- Quality scoring: automated LLM-judge evaluation on a sample of responses (faithfulness, relevance, citation accuracy)

### 21.3 Automated Evaluation

Regular evaluation runs assess RAG pipeline quality:
- **Faithfulness**: Do responses only contain information from retrieved sources?
- **Relevance**: Are retrieved documents relevant to the query?
- **Context precision**: Are the most relevant documents ranked highest?
- **Context recall**: Are all relevant documents retrieved?
- **Citation accuracy**: Do citations match their claimed sources?

Evaluation runs against a curated test query set per industry vertical. Results are tracked over time to detect regressions.

### 21.4 Alerting

| Alert | Condition | Severity |
|---|---|---|
| Lex unavailable | Self-hosted Lex health check fails for > 5 minutes | Critical |
| High error rate | > 5% of requests returning errors in a 5-minute window | Critical |
| Latency regression | p95 latency > 2Ã— baseline for 10 minutes | Warning |
| Credit exhaustion | Any tenant at > 95% credit usage | Warning |
| Citation verification failure rate | > 10% of citations removed in a 1-hour window | Warning |
| Dead letter queue growth | > 50 items in dead letter queue | Warning |
| Evaluation score drop | Any evaluation metric drops > 10% from baseline | Warning |

---

## 22. API Design

### 22.1 API Versioning

- URI-based versioning: `/api/v1/`, `/api/v2/`
- N-1 version support: the previous API version is maintained for at least 12 months after a new version is released
- Deprecation notices: 6 months advance notice before a version is retired
- Changelog published per version

### 22.2 Webhooks

Tenants can configure webhook endpoints to receive event notifications:

| Event | Payload |
|---|---|
| `document.processing.complete` | `{document_id, knowledge_base_id, status}` |
| `document.processing.failed` | `{document_id, error_code, error_message}` |
| `policy_review.complete` | `{review_id, overall_rating, summary}` |
| `policy_review.failed` | `{review_id, error_code, error_message}` |
| `regulatory_change.detected` | `{alert_id, change_type, summary, affected_policies}` |
| `credit.threshold_reached` | `{tenant_id, percentage, credits_remaining}` |

**Webhook delivery:**
- HMAC-SHA256 signature verification (shared secret per tenant)
- Retry with exponential backoff (1s, 5s, 30s, 5min, 30min) â€” 5 attempts
- Webhook delivery logs viewable in admin dashboard

### 22.3 Rate Limiting

- Per-tenant rate limits on all API endpoints
- Default: 100 requests/minute for standard endpoints, 10 requests/minute for AI endpoints
- Rate limit headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`
- Enterprise tenants can request custom rate limits

---

## Appendix A: Lex API â€” Self-Hosting Reference

For production deployment (recommended) and tenants requiring a self-hosted Lex instance:

**Prerequisites:**
- Python 3.12+
- Docker & Docker Compose
- Azure OpenAI credentials (for embedding generation)
- Qdrant (local or cloud)

**Quick Start:**
```
git clone https://github.com/i-dot-ai/lex.git && cd lex
cp .env.example .env  # Add Azure OpenAI keys
docker compose up -d
make ingest-all-full  # Full dataset (8+ hours)
```

**Architecture:**
```
lex/
â”œâ”€â”€ src/
â”‚   â”œâ”€â”€ lex/          # Data pipeline (scraping, parsing, indexing)
â”‚   â””â”€â”€ backend/      # API server (FastAPI + MCP)
â”œâ”€â”€ tools/            # Export utilities (Parquet/JSONL)
â””â”€â”€ docs/             # Documentation
```

**Bulk Downloads (alternative to running pipeline):**
- `legislation.parquet` â€” All Acts and SIs
- `explanatory_note.parquet` â€” Explanatory notes
- `amendment.parquet` â€” Legislative amendments
- Legislation sections split by year (Snappy-compressed Parquet)
- Updated weekly (Sundays at 03:00 UTC)

**Automated Weekly Refresh:**
A scheduled job downloads the latest Parquet files, compares against the current dataset, identifies changes (new legislation, amendments, repeals), and triggers the regulatory change detection pipeline (Section 3.8).

---

## Appendix B: Tenant Configuration Schema (Illustrative)

```yaml
tenant:
  id: "uuid"
  name: "Acme Housing Association"
  slug: "acme-housing"
  industry_vertical: "social-housing"

  branding:
    app_name: "Acme PolicyAI"
    logo_url: "https://..."
    primary_colour: "#1a365d"
    secondary_colour: "#2b6cb0"
    favicon_url: "https://..."
    custom_domain: "ai.acmehousing.org.uk"
    disclaimer_text: "This is AI-generated information..."
    pdf_header_logo_url: "https://..."
    email_template_logo_url: "https://..."

  subscription:
    tier: "professional"
    credit_limit: 500000
    billing_period: "monthly"
    max_users: 50
    model_routing: "default"  # or "prefer-opus" for Enterprise

  knowledge_base:
    legislation:
      source: "lex-self-hosted"
      lex_endpoint: "https://lex.internal.yourai.com/mcp"
      lex_rest_endpoint: "https://lex.internal.yourai.com/api"
      fallback_endpoint: "https://lex.lab.i.ai.gov.uk/mcp"
    company_policy:
      enabled: true
    sector_knowledge:
      enabled: true
    case_law:
      source: "lex-self-hosted"
    parliamentary:
      enabled: true
      source: "parliament-mcp-self-hosted"
      endpoint: "https://parliament.internal.yourai.com/mcp"

  ai_behaviour:
    confidence_display: true
    citation_verification: true
    mandatory_disclaimer: true
    topic_restrictions: []
    british_english: true

  external_sources:
    - name: "RSH Standards"
      type: "regulatory-standards"
      endpoint: "https://..."
      enabled: true
      polling_interval: "1h"
    - name: "Housing Ombudsman"
      type: "ombudsman"
      endpoint: "https://..."
      enabled: true
      sub_agent: true
    - name: "Gov.uk Consultations"
      type: "government-consultations"
      endpoint: "https://..."
      enabled: true

  regulatory_monitoring:
    enabled: true
    notification_email: "compliance@acmehousing.org.uk"
    alert_frequency: "immediate"  # or "daily-digest"

  news_feeds:
    - url: "https://example.com/rss"
      name: "Inside Housing"

  job_roles:
    - "Housing Officer"
    - "Property Manager"
    - "Maintenance Manager"
    - "Director"
    - "Other"

  default_personas:
    - name: "Asset & Compliance Lead"
      description: "Focus on regulatory compliance..."
      system_instructions: "..."
      skills: ["legal-research", "case-law-analysis"]
    - name: "Customer Experience Lead"
      description: "..."
      system_instructions: "..."
      skills: ["complaint-handling"]

  conversation_templates:
    - name: "Building Safety Act obligations"
      prompt: "Review our obligations under the Building Safety Act 2022 for..."
      category: "compliance"
    - name: "RSH consumer standards"
      prompt: "What are the current RSH consumer standards requirements for..."
      category: "regulatory"

  data_retention:
    conversations: "3y"
    policy_reviews: "7y"
    audit_logs: "7y"
    semantic_cache_ttl: "30d"

  webhooks:
    - url: "https://acmehousing.org.uk/webhooks/yourai"
      secret: "hmac-shared-secret"
      events: ["policy_review.complete", "regulatory_change.detected"]
```

---

## Appendix C: i.AI Ecosystem Integration Map

YourAI integrates with and builds upon the UK Government's Incubator for AI (i.AI) open-source ecosystem. This appendix maps the integration points.

| i.AI Project | YourAI Integration | Priority |
|---|---|---|
| **Lex** (`i-dot-ai/lex`) | Primary UK legislation and case law data source (self-hosted) | Critical â€” MVP |
| **Parliament MCP** (`i-dot-ai/parliament-mcp`) | Optional parliamentary data source (Hansard, Written Questions, committees) | High â€” Phase 2 |
| **awesome-gov-datasets** (`i-dot-ai/awesome-gov-datasets`) | Discovery catalogue for identifying additional data sources per industry vertical | Medium â€” Phase 2 |
| **uwotm8** (`i-dot-ai/uwotm8`) | British English consistency in AI-generated outputs (post-processing or prompt guidance) | Low â€” Phase 3 |
| **ThemeFinder** (`i-dot-ai/themefinder`) | Analysis of user query patterns to identify knowledge base gaps and popular topics | Low â€” Phase 3 |

All i.AI tools are MIT licensed. Data sources use Open Government Licence v3.0, Open Justice Licence, or Open Parliament Licence. Attribution requirements apply.

YourAI is complementary to i.AI's tools, not competitive. i.AI builds internal government tools; YourAI distributes compliance AI to regulated industries commercially via white-label partnerships.

---

## Appendix D: Glossary

| Term | Definition |
|---|---|
| **BM25** | Best Matching 25, a keyword-based text ranking algorithm used alongside vector search |
| **Chunk** | A segment of a document, typically 256â€“512 tokens, used as the unit of retrieval in semantic search |
| **Citation Verification** | The process of independently confirming that a cited legal source exists and accurately represents the claim |
| **Contextual Retrieval** | Technique of prepending a brief summary to each chunk describing its position in the overall document before embedding |
| **Cross-encoder Reranking** | A model that jointly evaluates query-document pairs to reorder search results by relevance |
| **Dead Letter Queue** | A queue for messages/jobs that have failed processing after the maximum retry count |
| **Hybrid Search** | Combining vector (semantic) search with keyword (BM25) search using rank fusion |
| **Lex API** | Open-source UK legal data platform by i.AI providing legislation, case law, amendments, and explanatory notes |
| **MCP** | Model Context Protocol â€” a standard for connecting AI models to external tools and data sources |
| **Namespace-per-tenant** | Vector database isolation strategy where each tenant's embeddings are stored in a separate namespace |
| **Persona** | A configured AI behaviour profile that modifies the assistant's tone, focus, and domain expertise |
| **Policy Ontology** | The structured taxonomy of policy definitions, compliance criteria, and scoring rubrics for a tenant's industry |
| **RAG (compliance)** | Red/Amber/Green rating system for policy compliance assessment |
| **RAG (retrieval)** | Retrieval-Augmented Generation â€” using retrieved documents to ground AI responses |
| **Reciprocal Rank Fusion (RRF)** | A method for combining ranked result lists from multiple search methods |
| **RLS** | Row-Level Security â€” database-level access control that restricts rows visible to each tenant |
| **Semantic Cache** | A cache that matches queries by meaning similarity (not exact text match) to serve repeated compliance questions faster |
| **Skills Pattern** | Automatic injection of domain-specific context into the AI prompt when relevant tools are activated |
