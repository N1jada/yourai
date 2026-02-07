"use client";

/**
 * Combined Providers — Wraps the app with all client-side providers.
 */

import { QueryProvider } from "./query-provider";
import { ToastProvider } from "@/components/ui/toast";
import { AuthProvider } from "@/lib/auth/auth-context";
import { ErrorBoundary } from "@/components/error-boundary";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <QueryProvider>
      <AuthProvider>
        <ToastProvider>
          <ErrorBoundary>{children}</ErrorBoundary>
        </ToastProvider>
      </AuthProvider>
    </QueryProvider>
  );
}
