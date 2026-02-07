/**
 * ConfidenceIndicator — Colour-coded badge showing response confidence level.
 * Uses text labels alongside colour (WCAG: never colour alone).
 */

import { cn } from "@/lib/utils/cn";
import type { ConfidenceLevel } from "@/lib/types/enums";

const levelConfig: Record<
  ConfidenceLevel,
  { label: string; className: string; description: string }
> = {
  high: {
    label: "High confidence",
    className: "bg-green-100 text-green-800 border-green-300",
    description: "Multiple corroborating sources found and verified",
  },
  medium: {
    label: "Medium confidence",
    className: "bg-amber-100 text-amber-800 border-amber-300",
    description: "This area may have limited coverage in our knowledge base",
  },
  low: {
    label: "Low confidence",
    className: "bg-red-100 text-red-800 border-red-300",
    description: "Limited sources available — verify this information independently",
  },
};

interface ConfidenceIndicatorProps {
  level: ConfidenceLevel;
  reason?: string;
  className?: string;
}

export function ConfidenceIndicator({
  level,
  reason,
  className,
}: ConfidenceIndicatorProps) {
  const config = levelConfig[level];

  return (
    <div
      className={cn(
        "inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-xs font-medium",
        config.className,
        className,
      )}
      title={reason || config.description}
      role="status"
      aria-label={`Confidence: ${config.label}`}
    >
      <span
        className={cn(
          "h-2 w-2 rounded-full",
          level === "high" && "bg-green-600",
          level === "medium" && "bg-amber-600",
          level === "low" && "bg-red-600",
        )}
        aria-hidden="true"
      />
      {config.label}
    </div>
  );
}
