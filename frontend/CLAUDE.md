# Frontend — YourAI

## Quick Reference

```bash
pnpm dev                    # Dev server (port 3000)
pnpm build                  # Production build
pnpm lint                   # ESLint
pnpm type-check             # TypeScript check
pnpm test                   # Vitest
```

## Architecture

```
src/
├── app/                    # Next.js App Router pages
│   ├── (auth)/             # Login, callback, error pages
│   └── (main)/             # Authenticated pages
│       ├── conversations/  # Chat interface
│       ├── knowledge-base/ # Document management
│       ├── policy-review/  # Compliance review
│       ├── admin/          # Admin dashboard
│       └── profile/        # User profile
├── components/             # React components by domain
├── lib/                    # API clients, hooks, utilities
│   ├── api/                # Base API client (all API calls go through here)
│   ├── auth/               # Token storage, refresh, auth context
│   └── streaming/          # SSE client, event parsing
└── stores/                 # Zustand state management
```

## Rules

1. **No `any`**: Strict TypeScript throughout.
2. **Server Components by default**: Only add `"use client"` when needed.
3. **API client only**: Never `fetch()` from components — use `lib/api/client.ts`.
4. **WCAG 2.2 AA**: Keyboard operable, ARIA attributes, 4.5:1 contrast.
5. **TanStack Query**: For all server state.
6. **Zustand**: For client-side state only.
