# YourAI Frontend

Next.js 15 frontend for YourAI compliance platform.

## Tech Stack

- **Framework**: Next.js 15 (App Router)
- **UI**: React 19, TypeScript, Tailwind CSS
- **Components**: Radix UI primitives + custom components
- **State**: TanStack Query (server state) + Zustand (client state)
- **Streaming**: EventSource (SSE) for real-time agent responses
- **Testing**: Vitest (unit) + Playwright (E2E)

## Getting Started

### Prerequisites

- Node.js 18+
- pnpm 8+

### Installation

```bash
# Install dependencies
pnpm install

# Create environment file
cp .env.local.example .env.local
# Edit .env.local and set NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

### Development

```bash
# Start dev server (http://localhost:3000)
pnpm dev

# Type check
pnpm type-check

# Run tests
pnpm test

# Run E2E tests
pnpm test:e2e
```

### Building

```bash
# Production build
pnpm build

# Start production server
pnpm start
```

## Project Structure

```
src/
├── app/                      # Next.js App Router
│   ├── (auth)/login/         # Login page
│   ├── (main)/               # Authenticated app shell
│   │   ├── conversations/    # Chat interface
│   │   └── layout.tsx        # Sidebar layout
│   ├── globals.css           # Global styles + Tailwind
│   └── layout.tsx            # Root layout with AuthProvider
├── components/
│   ├── ui/                   # Base UI components (Button, Input, etc.)
│   └── conversation/         # Chat-specific components
│       ├── message-list.tsx
│       ├── message-bubble.tsx
│       └── chat-input.tsx
├── lib/
│   ├── api/                  # API client
│   │   ├── client.ts         # Base HTTP client with auth
│   │   ├── endpoints.ts      # Typed API methods
│   │   └── types.ts          # TypeScript types for API
│   ├── auth/                 # Authentication
│   │   ├── auth-context.tsx  # React context + hooks
│   │   └── token-storage.ts  # LocalStorage token management
│   ├── streaming/            # SSE client
│   │   └── sse-client.ts
│   └── utils/
│       └── cn.ts             # className utility
└── stores/                   # Zustand stores (future)
```

## Features Implemented (WP7a + WP7b)

### Phase 1: Project Setup ✓
- Package.json with all dependencies
- TypeScript, Tailwind, PostCSS configuration
- Vitest + Playwright test configuration
- ESLint + type checking

### Phase 2: API Client & Auth ✓
- Base API client with automatic auth header injection
- Typed API endpoints for all backend routes
- Token storage (localStorage) with expiry tracking
- Auth context provider with login/logout

### Phase 3: Authentication UI ✓
- Login page with form validation
- Auth redirect middleware
- User session management

### Phase 4: App Shell ✓
- Sidebar navigation layout
- User menu with sign-out
- Responsive layout structure
- Tenant branding via CSS custom properties

### Phase 5: Conversation Interface ✓
- Conversations list page
- Individual conversation view
- Message list with auto-scroll
- Message bubbles (user/assistant)
- Chat input with keyboard shortcuts (Enter to send, Shift+Enter for newline)

### Phase 6: SSE Streaming ✓
- EventSource-based SSE client
- Real-time content deltas
- Connection management with cleanup
- Event type discrimination

### Phase 7: Message Features (Partial)
- Confidence badges (high/medium/low)
- Streaming indicator (animated cursor)
- TODO: Citation rendering with verification badges
- TODO: Persona selector

## Environment Variables

Create `.env.local`:

```bash
# Backend API base URL
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

## Testing

### Unit Tests

```bash
# Run all unit tests
pnpm test

# Watch mode
pnpm test:watch

# With UI
pnpm test:ui
```

### E2E Tests

```bash
# Run E2E tests
pnpm test:e2e

# Interactive mode
pnpm test:e2e:ui
```

## Code Quality

- **TypeScript**: Strict mode, no `any`
- **ESLint**: Next.js + TypeScript rules
- **Accessibility**: WCAG 2.2 AA compliant (focus rings, ARIA attributes, keyboard navigation)
- **Responsive**: Mobile-first design

## Next Steps

- [ ] Citation rendering with verification badges
- [ ] Persona selector component
- [ ] Knowledge base document upload UI
- [ ] Admin settings pages
- [ ] Dark mode support
- [ ] Offline support
- [ ] Performance optimization (React.memo, useMemo, lazy loading)

## Contributing

See `CLAUDE.md` for coding standards and conventions.
