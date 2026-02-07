"use client";

/**
 * Toast — Lightweight toast notification system using Radix Toast.
 */

import { useState, useCallback, createContext, useContext } from "react";
import * as ToastPrimitive from "@radix-ui/react-toast";
import { X } from "lucide-react";
import { cn } from "@/lib/utils/cn";

type ToastVariant = "default" | "success" | "error";

interface Toast {
  id: string;
  title: string;
  description?: string;
  variant: ToastVariant;
}

interface ToastContextValue {
  toast: (opts: { title: string; description?: string; variant?: ToastVariant }) => void;
}

const ToastContext = createContext<ToastContextValue | undefined>(undefined);

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within ToastProvider");
  return ctx;
}

let toastId = 0;

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const addToast = useCallback(
    (opts: { title: string; description?: string; variant?: ToastVariant }) => {
      const id = String(++toastId);
      setToasts((prev) => [...prev, { id, variant: "default", ...opts }]);
    },
    [],
  );

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  return (
    <ToastContext.Provider value={{ toast: addToast }}>
      <ToastPrimitive.Provider swipeDirection="right" duration={5000}>
        {children}

        {toasts.map((t) => (
          <ToastPrimitive.Root
            key={t.id}
            className={cn(
              "rounded-lg border bg-white p-4 shadow-lg",
              "data-[state=open]:animate-in data-[state=closed]:animate-out",
              "data-[state=closed]:fade-out-80 data-[state=open]:fade-in-0",
              "data-[state=closed]:slide-out-to-right-full data-[state=open]:slide-in-from-top-full",
              t.variant === "error" && "border-red-200 bg-red-50",
              t.variant === "success" && "border-green-200 bg-green-50",
            )}
            onOpenChange={(open: boolean) => {
              if (!open) removeToast(t.id);
            }}
          >
            <div className="flex items-start gap-3">
              <div className="flex-1">
                <ToastPrimitive.Title className="text-sm font-semibold text-neutral-900">
                  {t.title}
                </ToastPrimitive.Title>
                {t.description && (
                  <ToastPrimitive.Description className="mt-1 text-sm text-neutral-600">
                    {t.description}
                  </ToastPrimitive.Description>
                )}
              </div>
              <ToastPrimitive.Close className="rounded-md p-1 text-neutral-400 hover:text-neutral-600">
                <X className="h-4 w-4" />
                <span className="sr-only">Close</span>
              </ToastPrimitive.Close>
            </div>
          </ToastPrimitive.Root>
        ))}

        <ToastPrimitive.Viewport className="fixed bottom-0 right-0 z-50 flex max-h-screen w-full flex-col gap-2 p-4 sm:max-w-md" />
      </ToastPrimitive.Provider>
    </ToastContext.Provider>
  );
}
