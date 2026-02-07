# WP7 Frontend — Outstanding Feature Plan

> Generated: 2026-02-07
> Branch: `main` (work on a `wp7/...` feature branch)
> Source of truth: `FUNCTIONAL_SPEC_V2.md` §3.1–3.10, `.claude/agents/frontend.md`

---

## Current State Summary

### What Exists (Implemented in WP7 Phase 1–6)

| Area | Files | Status |
|---|---|---|
| **Root layout** | `app/layout.tsx` | Basic HTML shell, no tenant branding |
| **Auth — login page** | `app/(auth)/login/page.tsx` | Basic login form |
| **Auth — context** | `lib/auth/auth-context.tsx`, `token-storage.ts` | Token storage, refresh, user context |
| **App shell** | `app/(main)/layout.tsx` | Sidebar with 3 nav links, user menu, logout |
| **Conversations list** | `app/(main)/conversations/page.tsx` | Paginated list, create button |
| **Conversation chat** | `app/(main)/conversations/[id]/page.tsx` | Load messages, send, SSE streaming |
| **Chat components** | `components/conversation/*` | ChatInput, MessageBubble, MessageList |
| **UI primitives** | `components/ui/*` | Button, Input, Textarea |
| **API client** | `lib/api/client.ts` | Base HTTP client with auth |
| **API endpoints** | `lib/api/endpoints.ts` | Auth, Conversations, Messages, Personas, KB, Documents |
| **SSE client** | `lib/streaming/sse-client.ts` | EventSource-based, typed events |
| **Type system** | `lib/types/*.ts` (11 files) | All contract-aligned types, enums, SSE events |

### What Does NOT Exist

- No Zustand stores (directory empty)
- No TanStack Query integration
- No knowledge base pages
- No policy review pages
- No admin dashboard pages
- No profile/settings page
- No citation/source display components
- No confidence indicator component
- No persona selector component
- No conversation template selector
- No file attachment support in chat
- No feedback (thumbs up/down) UI
- No cancel generation button
- No conversation rename/delete UI
- No conversation export
- No error boundaries or loading skeletons
- No tenant branding (CSS custom properties)
- No responsive/mobile layout
- No accessibility enhancements (ARIA, keyboard nav, screen reader)
- No news feed page
- No canvas workspace
- No tests (component, a11y, or E2E)

---

## Outstanding Features by Sub-Package

### WP7a: Shell & Navigation

| # | Feature | Spec Ref | Priority | Size | Depends On |
|---|---|---|---|---|---|
| a1 | **TanStack Query provider** — Wrap app in QueryClientProvider, configure stale times, error handling | frontend.md | P0 | S | — |
| a2 | **Zustand stores** — Create stores: `sidebar-store.ts` (open/closed, active nav), `streaming-store.ts` (streaming state per conversation), `persona-store.ts` (active persona) | frontend.md | P0 | M | — |
| a3 | **Tenant branding** — Fetch `TenantConfig` on login, apply CSS custom properties (`--color-primary`, `--color-secondary`), dynamic logo, app name, favicon | §1.1, frontend.md | P1 | M | Backend: `GET /api/v1/tenants/branding/{slug}` |
| a4 | **Sidebar conversation list** — Show recent conversations in sidebar (not just a nav link), search/filter, click to navigate | §3.1.1 | P0 | M | a1 |
| a5 | **Responsive layout** — Collapsible sidebar on mobile, hamburger menu, responsive breakpoints | frontend.md | P1 | M | a2 |
| a6 | **Error boundary** — Global error boundary component, per-route error.tsx files, toast notification system | — | P0 | M | — |
| a7 | **Loading skeletons** — Skeleton components for conversation list, message list, pages | — | P1 | S | — |
| a8 | **Active nav highlighting** — Use `usePathname()` to highlight current sidebar link | — | P0 | S | — |
| a9 | **Auth callback page** — `app/(auth)/callback/page.tsx` for OAuth redirect handling | frontend.md | P1 | S | — |
| a10 | **Auth error page** — `app/(auth)/error/page.tsx` for auth failure display | frontend.md | P1 | S | — |
| a11 | **Permission-gated navigation** — Show/hide admin link based on user roles/permissions | §3.4 | P1 | S | — |

### WP7b: Conversation Interface

| # | Feature | Spec Ref | Priority | Size | Depends On |
|---|---|---|---|---|---|
| b1 | **Persona selector** — Dropdown in chat input area to pick AI persona before sending | §3.1.5 | P0 | M | a1, backend persona routes |
| b2 | **Citation components** — `LegalSource`, `CaseLawSource`, `CompanyPolicySource`, `ParliamentarySource` cards rendered in message bubbles | §3.1.6 | P0 | L | — |
| b3 | **Confidence indicator** — Colour-coded badge (High/Medium/Low) with tooltip showing reason, displayed per assistant message | §3.1.9 | P0 | S | — |
| b4 | **Verification badge** — Shows citation verification status (Verified/Unverified/Pre-1963) on each legal source | §3.1.6 | P0 | S | b2 |
| b5 | **Agent progress display** — Show sub-agent start/progress/complete events as status chips during streaming | §3.1.10 | P0 | M | — |
| b6 | **SSE event handlers (full)** — Handle all 26 event types in conversation page: agent lifecycle, sources, confidence, usage metrics, verification, conversation state, errors | §3.1.10 | P0 | M | b2, b3 |
| b7 | **Cancel generation** — Button to cancel in-flight AI response, calls `POST /conversations/{id}/cancel` | §3.1.2 | P0 | S | Backend cancel route |
| b8 | **Conversation templates** — Show clickable template suggestions in empty conversation, calls `GET /conversation-templates` | §3.1.3 | P1 | M | Backend template route |
| b9 | **Feedback UI** — Thumbs up/down buttons on each assistant message, optional comment modal, calls `POST /messages/{id}/feedback` | §3.9 | P1 | M | Backend feedback route |
| b10 | **File attachments** — File picker button in chat input, preview attached files, send with message | §3.1.2 | P1 | M | Backend attachment support |
| b11 | **Conversation rename** — Inline-editable title in conversation header, calls `PATCH /conversations/{id}` | §3.1.1 | P1 | S | — |
| b12 | **Conversation delete** — Delete button with confirmation modal, calls `DELETE /conversations/{id}` | §3.1.1 | P1 | S | — |
| b13 | **Usage metrics display** — Token count (input/output) shown in conversation footer or collapsible panel | §3.1.2 | P2 | S | — |
| b14 | **Mandatory disclaimer** — Display tenant-configured disclaimer beneath each AI response | §3.1.8 | P1 | S | a3 (tenant config) |
| b15 | **Streaming acknowledgement** — Show "Analysing your question about..." within 1s of sending | §3.1.10 | P0 | S | — |
| b16 | **Message state indicators** — Visual indicators for message states (Pending, Success, Error, Cancelled) | §3.1.2 | P1 | S | — |
| b17 | **Scroll management** — Auto-scroll on new content, "scroll to bottom" button when scrolled up | — | P0 | S | — |
| b18 | **Conversation export** — Export as Markdown (button in header), calls `GET /conversations/{id}/export?format=markdown` | §3.10 | P2 | S | Backend export route |
| b19 | **Annotation display** — Render annotation events (expert commentary) in message metadata | §3.1.6 | P1 | S | b2 |
| b20 | **Migrate to TanStack Query** — Replace manual `useEffect` + `useState` data loading with `useQuery`/`useMutation` hooks | frontend.md | P0 | M | a1 |

### WP7c: Knowledge Base

| # | Feature | Spec Ref | Priority | Size | Depends On |
|---|---|---|---|---|---|
| c1 | **KB list page** — `app/(main)/knowledge-base/page.tsx` showing all knowledge bases with category badges, document counts, source types | §3.2.1 | P0 | M | a1 |
| c2 | **KB detail page** — `app/(main)/knowledge-base/[id]/page.tsx` with document table (name, status, size, chunk count, last indexed) | §3.2.2 | P0 | M | c1 |
| c3 | **Document upload** — Drag-and-drop + file picker, supported formats (PDF/DOCX/TXT), 50MB limit, progress indicator | §3.2.2 | P0 | L | c2 |
| c4 | **Processing status component** — Real-time document processing state display with 9 states (uploaded → ready/failed), progress bar or step indicator | §3.2.3 | P0 | M | — |
| c5 | **Document detail page** — `app/(main)/knowledge-base/[id]/documents/[docId]/page.tsx` with metadata, version history, processing timeline | §3.2.2 | P1 | M | c2 |
| c6 | **Version history** — Show document versions with dates, allow revert to previous version | §3.2.2 | P2 | M | c5 |
| c7 | **Folder browser** — Hierarchical folder structure for organising documents within a KB | §3.2.2 | P2 | L | c2 |
| c8 | **Bulk delete** — Checkbox selection + bulk delete action for multiple documents | §3.2.2 | P2 | S | c2 |
| c9 | **Search within KB** — Search bar on KB page, calls hybrid search API, displays results with relevance scores | §3.2.4 | P1 | M | Backend search endpoint |
| c10 | **KB API endpoints** — Add missing endpoints: `createKnowledgeBase`, `deleteKnowledgeBase`, `getDocumentVersions` to `endpoints.ts` | — | P0 | S | — |

### WP7d: Policy Review

| # | Feature | Spec Ref | Priority | Size | Depends On |
|---|---|---|---|---|---|
| d1 | **Policy review list page** — `app/(main)/policy-review/page.tsx` showing past reviews with status, date, policy type, RAG score | §3.3.5 | P1 | M | a1, WP6 backend |
| d2 | **Policy review trigger** — "Policy Rating" button (in conversation or standalone), upload document, start review | §3.3.1 | P1 | L | WP6 backend |
| d3 | **Review progress display** — Real-time SSE progress during policy review (PolicyReviewStatus, CitationProgress events) | §3.3.4 | P1 | M | WP6 backend |
| d4 | **Review results page** — `app/(main)/policy-review/[id]/page.tsx` with structured output: RAG ratings, compliance criteria, gap analysis, citations | §3.3.3 | P1 | L | d2, WP6 backend |
| d5 | **RAG scoring display** — Red/Amber/Green rating badges with text labels (never colour alone per WCAG) | §3.3.3 | P1 | S | — |
| d6 | **PDF export** — Export policy review as branded PDF report | §3.3.1 | P2 | M | WP6 backend, a3 |
| d7 | **Review comparison** — Compare two reviews of the same policy type over time | §3.3.5 | P2 | L | d4, WP6 backend |
| d8 | **Cancel review** — Cancel in-progress policy review | §3.3.1 | P1 | S | WP6 backend |

> **Note**: WP7d depends heavily on WP6 (Policy Review & Compliance) backend, which is not yet started. Features are included for completeness but should be deferred until WP6 is built.

### WP7e: Admin Dashboard

| # | Feature | Spec Ref | Priority | Size | Depends On |
|---|---|---|---|---|---|
| e1 | **Admin layout** — `app/(main)/admin/layout.tsx` with sub-navigation tabs (Dashboard, Users, Personas, Guardrails, Activity Log) | §3.4 | P0 | M | a11 |
| e2 | **Analytics dashboard** — `app/(main)/admin/page.tsx` with stat cards (credit usage, conversations, users, reviews, avg confidence) | §3.4.1 | P1 | L | Backend analytics endpoint (not yet built) |
| e3 | **Time series charts** — Credit usage, conversations, users over time with date range filtering (presets + custom) | §3.4.1 | P2 | L | e2, charting library |
| e4 | **User management page** — `app/(main)/admin/users/page.tsx` with searchable/filterable user table, status badges, role display | §3.4.2 | P0 | L | a1 |
| e5 | **User invite modal** — Create user form (email, name, role assignment), bulk invite via CSV | §3.4.2 | P1 | M | e4, Backend user routes |
| e6 | **User edit** — Edit user details, change roles, change status (active/disabled) | §3.4.2 | P1 | M | e4 |
| e7 | **Persona management page** — `app/(main)/admin/personas/page.tsx` with CRUD table, create/edit form (name, description, system instructions, activated skills) | §3.4.3 | P1 | L | a1, Backend persona routes |
| e8 | **Persona duplicate** — "Duplicate" action on persona list row | §3.4.3 | P2 | S | e7 |
| e9 | **Guardrail management page** — `app/(main)/admin/guardrails/page.tsx` with CRUD, status indicators, configuration rules editor | §3.4.4 | P1 | L | Backend guardrail routes |
| e10 | **Activity log page** — `app/(main)/admin/activity-log/page.tsx` with filterable log table (tag, user, date), CSV export button | §3.4.5 | P1 | M | Backend activity log routes |
| e11 | **Admin API endpoints** — Add to `endpoints.ts`: users CRUD, roles CRUD, guardrails CRUD, activity logs, tenant config update, analytics | — | P0 | M | — |
| e12 | **Knowledge base analytics** — Most queried topics, knowledge gaps, document usage stats | §3.4.1 | P2 | M | e2, Backend analytics |
| e13 | **Feedback analytics** — Satisfaction rate, common complaints, lowest-rated topics dashboard panel | §3.9 | P2 | M | e2, b9 |
| e14 | **Regulatory change panel** — Dashboard panel showing pending regulatory changes with acknowledge/dismiss actions | §3.8.3 | P2 | M | WP6 backend |
| e15 | **Compliance calendar** — Calendar view of upcoming policy review dates and regulatory changes | §3.8.4 | P2 | L | WP6 backend |

### WP7f: User Profile & Settings

| # | Feature | Spec Ref | Priority | Size | Depends On |
|---|---|---|---|---|---|
| f1 | **Profile page** — `app/(main)/profile/page.tsx` with editable first/last name, job role dropdown, read-only email, avatar (Gravatar) | §3.7 | P0 | M | a1 |
| f2 | **Notification preferences** — Toggle email alerts for: regulatory changes, credit warnings, policy review completion | §3.7 | P1 | S | f1 |
| f3 | **Data export request** — GDPR Subject Access Request button (triggers backend job) | §3.7 | P2 | S | Backend GDPR endpoint |
| f4 | **Account deletion request** — GDPR Right to Erasure button with confirmation | §3.7 | P2 | S | Backend GDPR endpoint |

### Cross-cutting: News Feed & Canvas (Spec §3.5, §3.6)

| # | Feature | Spec Ref | Priority | Size | Depends On |
|---|---|---|---|---|---|
| x1 | **News feed page** — `app/(main)/news/page.tsx` with masonry grid of RSS feed stories, refresh button | §3.5 | P2 | M | Backend news feed endpoint (not built) |
| x2 | **Canvas workspace** — Expandable editor view for AI responses: rich text editing, auto-save, export as PDF/Markdown | §3.6 | P2 | L | Backend canvas API (not built) |

### Cross-cutting: Accessibility & Testing

| # | Feature | Spec Ref | Priority | Size | Depends On |
|---|---|---|---|---|---|
| t1 | **ARIA attributes** — `role="log"` on chat container, `aria-live="polite"` on new messages, "Response complete" announcement, focus management | §WCAG 2.2 AA, frontend.md | P0 | M | b6 |
| t2 | **Keyboard navigation** — All interactive elements keyboard-operable, visible focus rings, skip-to-content link | §WCAG 2.2 AA | P1 | M | — |
| t3 | **Colour contrast audit** — Ensure 4.5:1 minimum ratio, never use colour alone (RAG ratings need text labels) | §WCAG 2.2 AA | P1 | S | — |
| t4 | **Reduced motion** — Respect `prefers-reduced-motion` media query for streaming animations, transitions | §WCAG 2.2 AA | P1 | S | — |
| t5 | **Component tests** — React Testing Library tests for all new components | frontend.md | P1 | L | All components |
| t6 | **Accessibility tests** — `jest-axe` tests for every component | frontend.md | P1 | M | t5 |
| t7 | **E2E test: conversation flow** — Login → create conversation → send message → receive streamed response | frontend.md | P1 | L | All b* features |
| t8 | **E2E test: document upload** — Upload document → see processing status → search and find document | frontend.md | P2 | L | All c* features |

---

## Recommended Session Build Order

### Session 1: Infrastructure & Data Layer (P0 foundations)
**Goal**: Set up TanStack Query, Zustand, error handling — the plumbing everything else needs.

| Task | Ref | Est |
|---|---|---|
| Install TanStack Query + Zustand | a1, a2 | 15 min |
| Create `QueryClientProvider` wrapper in root layout | a1 | 15 min |
| Create Zustand stores: sidebar, streaming, persona | a2 | 30 min |
| Global error boundary + toast system | a6 | 30 min |
| Loading skeleton components | a7 | 20 min |
| Active nav highlighting in sidebar | a8 | 10 min |
| Admin API endpoints in `endpoints.ts` | e11 | 30 min |
| KB API endpoints in `endpoints.ts` | c10 | 15 min |

**Deliverable**: Foundation layer ready. All subsequent sessions can use hooks, stores, error handling.

### Session 2: Conversation Interface — Core UX (P0)
**Goal**: Make the chat experience production-quality with citations, confidence, agent progress.

| Task | Ref | Est |
|---|---|---|
| Confidence indicator component | b3 | 20 min |
| Verification badge component | b4 | 15 min |
| Citation components (Legal, CaseLaw, Policy, Parliamentary) | b2 | 60 min |
| Agent progress display (sub-agent chips) | b5 | 30 min |
| Full SSE event handler with all 26 event types | b6 | 45 min |
| Streaming acknowledgement ("Analysing...") | b15 | 10 min |
| Scroll management + auto-scroll | b17 | 20 min |
| Cancel generation button | b7 | 15 min |
| Migrate conversation page to TanStack Query | b20 | 40 min |

**Deliverable**: Full-featured chat with real-time citations, confidence, agent progress, cancel.

### Session 3: Conversation — Secondary Features
**Goal**: Polish conversation UX with remaining P1 features.

| Task | Ref | Est |
|---|---|---|
| Persona selector dropdown | b1 | 30 min |
| Feedback UI (thumbs up/down + comment) | b9 | 40 min |
| Conversation rename (inline edit) | b11 | 20 min |
| Conversation delete (with confirmation) | b12 | 15 min |
| Message state indicators | b16 | 15 min |
| Mandatory disclaimer on AI responses | b14 | 15 min |
| Annotation display in messages | b19 | 20 min |
| Sidebar conversation list (recent conversations) | a4 | 40 min |
| Conversation templates in empty state | b8 | 30 min |

**Deliverable**: Complete conversation interface matching spec §3.1.

### Session 4: Knowledge Base UI (P0 + P1)
**Goal**: Build the document management interface.

| Task | Ref | Est |
|---|---|---|
| KB list page with category badges | c1 | 40 min |
| KB detail page with document table | c2 | 40 min |
| Document upload (drag-and-drop + file picker) | c3 | 60 min |
| Processing status component (9-state step indicator) | c4 | 40 min |
| Document detail page | c5 | 30 min |
| Search within KB | c9 | 30 min |

**Deliverable**: Complete KB management matching spec §3.2.

### Session 5: Admin Dashboard — Core (P0 + P1)
**Goal**: Build the admin interface for user and persona management.

| Task | Ref | Est |
|---|---|---|
| Admin layout with sub-nav tabs | e1 | 30 min |
| User management page (table + search/filter) | e4 | 60 min |
| User invite modal | e5 | 30 min |
| User edit (roles, status) | e6 | 30 min |
| Persona management page (CRUD) | e7 | 60 min |
| Permission-gated navigation | a11 | 15 min |

**Deliverable**: Admin can manage users and personas.

### Session 6: Admin Dashboard — Extended + Profile
**Goal**: Guardrails, activity log, profile page.

| Task | Ref | Est |
|---|---|---|
| Guardrail management page | e9 | 60 min |
| Activity log page with filters + CSV export | e10 | 40 min |
| Profile page (edit name, job role, avatar) | f1 | 30 min |
| Notification preferences | f2 | 20 min |
| Analytics dashboard (stat cards) | e2 | 45 min |

**Deliverable**: Full admin dashboard and user profile matching spec §3.4, §3.7.

### Session 7: Shell Polish & Accessibility
**Goal**: Tenant branding, responsive design, WCAG compliance.

| Task | Ref | Est |
|---|---|---|
| Tenant branding (CSS custom properties, logo, colours) | a3 | 45 min |
| Responsive sidebar (collapsible, mobile hamburger) | a5 | 40 min |
| ARIA attributes across all components | t1 | 40 min |
| Keyboard navigation audit | t2 | 30 min |
| Colour contrast audit | t3 | 20 min |
| Reduced motion support | t4 | 15 min |
| Auth callback + error pages | a9, a10 | 20 min |

**Deliverable**: Accessible, branded, responsive application shell.

### Session 8: Testing
**Goal**: Component tests, accessibility tests, E2E.

| Task | Ref | Est |
|---|---|---|
| Install jest-axe, configure Vitest for component tests | — | 15 min |
| Component tests for all new components | t5 | 90 min |
| Accessibility tests with jest-axe | t6 | 45 min |
| E2E test: conversation flow | t7 | 60 min |

**Deliverable**: Test coverage for all implemented features.

### Session 9: Post-MVP Features (P2, when backend is ready)
**Goal**: Deferred features that depend on unbuilt backends or are post-MVP.

| Task | Ref | Blocked By |
|---|---|---|
| File attachments in chat | b10 | Backend attachment support |
| Conversation export (Markdown) | b18 | Backend export route |
| Usage metrics display | b13 | — |
| Document version history | c6 | — |
| Folder browser | c7 | — |
| Bulk delete documents | c8 | — |
| Persona duplicate | e8 | — |
| Time series charts | e3 | Charting library, backend analytics |
| KB analytics panel | e12 | Backend analytics |
| Feedback analytics panel | e13 | Backend analytics |
| News feed page | x1 | Backend news endpoint |
| Canvas workspace | x2 | Backend canvas API |
| GDPR data export + account deletion | f3, f4 | Backend GDPR endpoints |

### Session 10: Policy Review UI (P1, blocked on WP6)
**Goal**: Policy review interface — only buildable after WP6 backend is complete.

| Task | Ref | Blocked By |
|---|---|---|
| Policy review list page | d1 | WP6 |
| Policy review trigger + upload | d2 | WP6 |
| Review progress display (SSE) | d3 | WP6 |
| Review results page (RAG ratings, citations, gap analysis) | d4 | WP6 |
| RAG scoring display component | d5 | — |
| Cancel review | d8 | WP6 |
| PDF export | d6 | WP6 |
| Review comparison | d7 | WP6 |
| Regulatory change panel | e14 | WP6 |
| Compliance calendar | e15 | WP6 |

---

## Dependency Summary

```
Session 1 (Infrastructure)
├── Session 2 (Chat Core) ← depends on TanStack Query, stores
│   └── Session 3 (Chat Polish) ← depends on citation components
├── Session 4 (Knowledge Base) ← depends on TanStack Query
├── Session 5 (Admin Core) ← depends on TanStack Query, API endpoints
│   └── Session 6 (Admin Extended + Profile)
├── Session 7 (Shell + A11y) ← can run in parallel with 4–6
└── Session 8 (Testing) ← after all features

Session 9 (Post-MVP) ← blocked on various backend features
Session 10 (Policy Review) ← blocked on WP6
```

## Total Feature Count

| Priority | Count | Status |
|---|---|---|
| P0 (MVP-critical) | 27 | All buildable now (backend ready) |
| P1 (Important) | 32 | Most buildable; some depend on WP6 |
| P2 (Post-MVP) | 21 | Most blocked on unbuilt backends |
| **Total** | **80** | |
