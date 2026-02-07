/**
 * LegalSource — Displays a legislation citation with verification badge.
 */

import { ExternalLink } from "lucide-react";
import { VerificationBadge } from "./verification-badge";
import type { VerificationStatus } from "@/lib/types/enums";

interface LegalSourceProps {
  actName: string;
  section: string;
  uri: string;
  verificationStatus: VerificationStatus;
}

export function LegalSource({
  actName,
  section,
  uri,
  verificationStatus,
}: LegalSourceProps) {
  return (
    <div className="flex items-start gap-2 rounded-md border border-blue-100 bg-blue-50 px-3 py-2 text-sm">
      <div className="flex-1 min-w-0">
        <div className="font-medium text-blue-900">{actName}</div>
        <div className="text-blue-700">Section {section}</div>
        <div className="mt-1 flex items-center gap-2">
          <VerificationBadge status={verificationStatus} />
          {uri && (
            <a
              href={uri}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-xs text-blue-600 hover:underline"
            >
              View source <ExternalLink className="h-3 w-3" />
            </a>
          )}
        </div>
      </div>
    </div>
  );
}
