"use client";

/**
 * Auth Callback Page — Handles OAuth redirect with code exchange.
 */

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/lib/auth/auth-context";

function CallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { isAuthenticated } = useAuth();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const code = searchParams.get("code");
    const errorParam = searchParams.get("error");
    const errorDescription = searchParams.get("error_description");

    if (errorParam) {
      setError(errorDescription ?? errorParam);
      return;
    }

    if (!code) {
      setError("No authorisation code received");
      return;
    }

    // If already authenticated after token exchange, redirect
    if (isAuthenticated) {
      router.push("/conversations");
      return;
    }

    // The auth context handles token storage — redirect to login
    // to complete the flow if needed
    router.push("/login");
  }, [searchParams, isAuthenticated, router]);

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-neutral-50 px-4">
        <div className="w-full max-w-md text-center">
          <h1 className="text-2xl font-bold text-neutral-900">
            Authentication Failed
          </h1>
          <p className="mt-2 text-sm text-neutral-600">{error}</p>
          <a
            href="/login"
            className="mt-4 inline-block text-sm font-medium text-brand-600 hover:text-brand-700"
          >
            Return to sign in
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-neutral-50">
      <div className="text-center">
        <div className="mx-auto h-8 w-8 animate-spin rounded-full border-2 border-neutral-300 border-t-brand-600" />
        <p className="mt-4 text-sm text-neutral-600">Completing sign in...</p>
      </div>
    </div>
  );
}

export default function CallbackPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center bg-neutral-50">
          <div className="text-center">
            <div className="mx-auto h-8 w-8 animate-spin rounded-full border-2 border-neutral-300 border-t-brand-600" />
            <p className="mt-4 text-sm text-neutral-600">Loading...</p>
          </div>
        </div>
      }
    >
      <CallbackContent />
    </Suspense>
  );
}
