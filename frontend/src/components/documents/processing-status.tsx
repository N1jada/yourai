/**
 * ProcessingStatus — Step indicator showing document processing state.
 */

import { Check, Loader2, AlertCircle } from "lucide-react";
import { cn } from "@/lib/utils/cn";
import type { DocumentProcessingState } from "@/lib/types/enums";

const steps: { state: DocumentProcessingState; label: string }[] = [
  { state: "uploaded", label: "Uploaded" },
  { state: "validating", label: "Validating" },
  { state: "extracting_text", label: "Extracting" },
  { state: "chunking", label: "Chunking" },
  { state: "contextualising", label: "Contextualising" },
  { state: "embedding", label: "Embedding" },
  { state: "indexing", label: "Indexing" },
  { state: "ready", label: "Ready" },
];

function getStepIndex(state: DocumentProcessingState): number {
  if (state === "failed") return -1;
  return steps.findIndex((s) => s.state === state);
}

interface ProcessingStatusProps {
  state: DocumentProcessingState;
  errorMessage?: string | null;
  className?: string;
}

export function ProcessingStatus({ state, errorMessage, className }: ProcessingStatusProps) {
  const currentIndex = getStepIndex(state);
  const isFailed = state === "failed";

  return (
    <div className={cn("space-y-2", className)}>
      <div className="flex items-center gap-1">
        {steps.map((step, i) => {
          const isComplete = currentIndex > i;
          const isCurrent = currentIndex === i;

          return (
            <div key={step.state} className="flex items-center">
              <div
                className={cn(
                  "flex h-6 w-6 items-center justify-center rounded-full text-xs",
                  isComplete && "bg-green-100 text-green-700",
                  isCurrent && !isFailed && "bg-blue-100 text-blue-700",
                  !isComplete && !isCurrent && "bg-neutral-100 text-neutral-400",
                )}
                title={step.label}
              >
                {isComplete ? (
                  <Check className="h-3 w-3" />
                ) : isCurrent && !isFailed ? (
                  <Loader2 className="h-3 w-3 animate-spin" />
                ) : (
                  <span>{i + 1}</span>
                )}
              </div>
              {i < steps.length - 1 && (
                <div
                  className={cn(
                    "h-0.5 w-4",
                    isComplete ? "bg-green-300" : "bg-neutral-200",
                  )}
                />
              )}
            </div>
          );
        })}
      </div>

      <div className="text-xs text-neutral-600">
        {isFailed ? (
          <span className="flex items-center gap-1 text-red-600">
            <AlertCircle className="h-3 w-3" />
            Failed{errorMessage ? `: ${errorMessage}` : ""}
          </span>
        ) : state === "ready" ? (
          <span className="text-green-600">Ready for search</span>
        ) : (
          <span className="capitalize">{state.replace(/_/g, " ")}...</span>
        )}
      </div>
    </div>
  );
}

/** Compact inline badge variant. */
export function ProcessingBadge({ state }: { state: DocumentProcessingState }) {
  const isReady = state === "ready";
  const isFailed = state === "failed";

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium",
        isReady && "bg-green-100 text-green-700",
        isFailed && "bg-red-100 text-red-700",
        !isReady && !isFailed && "bg-blue-100 text-blue-700",
      )}
    >
      {!isReady && !isFailed && (
        <Loader2 className="h-3 w-3 animate-spin" />
      )}
      {isFailed && <AlertCircle className="h-3 w-3" />}
      {isReady && <Check className="h-3 w-3" />}
      <span className="capitalize">{state.replace(/_/g, " ")}</span>
    </span>
  );
}
