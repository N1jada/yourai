/**
 * Skeleton — Loading placeholder component.
 */

import { cn } from "@/lib/utils/cn";

interface SkeletonProps {
  className?: string;
}

export function Skeleton({ className }: SkeletonProps) {
  return (
    <div
      className={cn("animate-pulse rounded-md bg-neutral-200", className)}
      aria-hidden="true"
    />
  );
}

/** Skeleton row for list items. */
export function SkeletonRow({ className }: SkeletonProps) {
  return (
    <div className={cn("flex items-center gap-3 p-4", className)}>
      <Skeleton className="h-10 w-10 rounded-full" />
      <div className="flex-1 space-y-2">
        <Skeleton className="h-4 w-3/4" />
        <Skeleton className="h-3 w-1/2" />
      </div>
    </div>
  );
}

/** Skeleton for a message bubble. */
export function SkeletonMessage({ className }: SkeletonProps) {
  return (
    <div className={cn("space-y-2 p-4", className)}>
      <Skeleton className="h-4 w-full" />
      <Skeleton className="h-4 w-5/6" />
      <Skeleton className="h-4 w-2/3" />
    </div>
  );
}

/** Skeleton for a card. */
export function SkeletonCard({ className }: SkeletonProps) {
  return (
    <div
      className={cn(
        "rounded-lg border border-neutral-200 bg-white p-6 space-y-3",
        className,
      )}
    >
      <Skeleton className="h-5 w-2/5" />
      <Skeleton className="h-4 w-full" />
      <Skeleton className="h-4 w-4/5" />
    </div>
  );
}
