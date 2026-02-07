"use client";

/**
 * Auth Error Page — Displays authentication failure messages.
 */

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { AlertTriangle } from "lucide-react";

const errorMessages: Record<string, string> = {
  session_expired: "Your session has expired. Please sign in again.",
  unauthorized: "You do not have permission to access this resource.",
  account_disabled: "Your account has been disabled. Contact your administrator.",
  account_deleted: "This account no longer exists.",
  invalid_token: "Your authentication token is invalid. Please sign in again.",
};

function ErrorContent() {
  const searchParams = useSearchParams();
  const errorCode = searchParams.get("code") ?? "unknown";
  const message =
    searchParams.get("message") ??
    errorMessages[errorCode] ??
    "An authentication error occurred.";

  return (
    <div className="flex min-h-screen items-center justify-center bg-neutral-50 px-4">
      <div className="w-full max-w-md text-center">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-red-100">
          <AlertTriangle className="h-6 w-6 text-red-600" />
        </div>
        <h1 className="mt-4 text-2xl font-bold text-neutral-900">
          Authentication Error
        </h1>
        <p className="mt-2 text-sm text-neutral-600">{message}</p>
        <div className="mt-6">
          <Button asChild>
            <a href="/login">Return to Sign In</a>
          </Button>
        </div>
      </div>
    </div>
  );
}

export default function AuthErrorPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center bg-neutral-50">
          <div className="text-center">
            <div className="mx-auto h-8 w-8 animate-spin rounded-full border-2 border-neutral-300 border-t-brand-600" />
          </div>
        </div>
      }
    >
      <ErrorContent />
    </Suspense>
  );
}
