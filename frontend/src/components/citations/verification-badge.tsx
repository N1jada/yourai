/**
 * VerificationBadge — Shows citation verification status.
 */

import { CheckCircle, AlertCircle, Clock, HelpCircle } from "lucide-react";
import { cn } from "@/lib/utils/cn";
import type { VerificationStatus } from "@/lib/types/enums";

const statusConfig: Record<
  VerificationStatus,
  { icon: React.ComponentType<{ className?: string }>; label: string; className: string }
> = {
  verified: {
    icon: CheckCircle,
    label: "Verified",
    className: "text-green-700 bg-green-50 border-green-200",
  },
  unverified: {
    icon: AlertCircle,
    label: "Unverified",
    className: "text-amber-700 bg-amber-50 border-amber-200",
  },
  removed: {
    icon: HelpCircle,
    label: "Removed",
    className: "text-red-700 bg-red-50 border-red-200",
  },
  pre_1963_digitised: {
    icon: Clock,
    label: "AI-digitised (pre-1963)",
    className: "text-neutral-700 bg-neutral-50 border-neutral-200",
  },
};

interface VerificationBadgeProps {
  status: VerificationStatus;
  className?: string;
}

export function VerificationBadge({ status, className }: VerificationBadgeProps) {
  const config = statusConfig[status];
  const Icon = config.icon;

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium",
        config.className,
        className,
      )}
    >
      <Icon className="h-3 w-3" />
      {config.label}
    </span>
  );
}
