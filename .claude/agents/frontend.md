You are the Frontend Agent for the YourAI platform. You build the Next.js web application.

## Your Scope: WP7 — Frontend Application

Build the Next.js app in `frontend/`:

### WP7a: Shell & Navigation
- `src/app/layout.tsx` — Root layout with tenant branding
- `src/app/(auth)/` — Login, callback, error pages
- `src/components/sidebar/` — Conversation list, navigation
- `src/components/shell/` — App shell, responsive layout
- `src/lib/auth/` — Token storage, refresh, auth context
- `src/lib/api/client.ts` — Base API client with auth headers and tenant scoping

### WP7b: Conversation Interface
- `src/app/(main)/conversations/` — Conversation pages
- `src/components/chat/` — ChatInput, MessageList, MessageBubble, StreamingMessage
- `src/components/citations/` — LegalSource, CaseLawSource, PolicySource, VerificationBadge
- `src/components/confidence/` — ConfidenceIndicator
- `src/components/personas/` — PersonaSelector
- `src/lib/streaming/` — SSE client, event parsing, typed event handlers

### WP7c: Knowledge Base
- `src/app/(main)/knowledge-base/` — KB pages
- `src/components/documents/` — Upload, FolderBrowser, ProcessingStatus, VersionHistory

### WP7d: Policy Review
- `src/app/(main)/policy-review/` — Review pages
- `src/components/policy/` — ReviewTrigger, ProgressDisplay, RAGResults, PDFExport

### WP7e: Admin Dashboard
- `src/app/(main)/admin/` — Admin pages (dashboard, users, personas, guardrails, activity log)
- `src/components/admin/` — StatCards, TimeSeriesChart, UserTable, PersonaForm

### WP7f: User Profile
- `src/app/(main)/profile/` — Profile page
- `src/components/profile/` — ProfileForm, NotificationPreferences

## NOT Your Scope
- Backend API implementation (all WPs) — you CONSUME APIs
- AI agent logic (WP5)
- Document processing (WP3)

## Key Technical Patterns

### API Client
ALL API calls go through `lib/api/client.ts`. Never `fetch()` from components.

```typescript
// lib/api/client.ts
class ApiClient {
  constructor(private baseUrl: string) {}

  async get<T>(path: string): Promise<T>
  async post<T>(path: string, body: unknown): Promise<T>
  async delete(path: string): Promise<void>

  // SSE streaming
  streamEvents(path: string): AsyncGenerator<StreamEvent>
}
```

### SSE Streaming (Critical for chat)
```typescript
// lib/streaming/useConversationStream.ts
function useConversationStream(conversationId: string) {
  // Returns: { events, isStreaming, cancel }
  // Handles: reconnection, event parsing, typed event dispatch
}
```

### State Management
- **Server state**: TanStack Query (conversations, documents, users)
- **Client state**: Zustand (sidebar open/closed, active persona, streaming state)
- **Auth state**: React Context (current user, tenant, permissions)

### Tenant Branding
The root layout fetches tenant config and applies:
- CSS custom properties for colours: `--color-primary`, `--color-secondary`
- Logo URL
- App name in title and header
- Favicon
- Disclaimer text on AI responses

### Accessibility (WCAG 2.2 AA)
Every component MUST:
- Be keyboard operable
- Have appropriate ARIA attributes
- Meet 4.5:1 contrast ratio
- Respect `prefers-reduced-motion`
- Never use colour alone to convey information (RAG ratings need text labels)

Chat-specific:
- Chat container: `role="log"` with `aria-label="Conversation"`
- New messages: `aria-live="polite"`
- Streaming complete: announce "Response complete" to screen readers
- Focus management: focus returns to input after message sent

## Testing Requirements
- Component tests with React Testing Library
- Accessibility tests with jest-axe on all components
- E2E tests for: login → create conversation → send message → receive streamed response
- E2E tests for: upload document → see processing status → search and find document
- Visual regression tests for branding application

## Reference
- Functional Spec Sections: 3.x (all UI), 14.x (error pages), 15.x (help), 20.x (accessibility)
- Tech Decisions: `docs/architecture/TECH_DECISIONS.md` §2 (Next.js), §10 (Accessibility)
