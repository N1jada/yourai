/**
 * ParliamentarySource — Displays a parliamentary data citation.
 */

import { Landmark } from "lucide-react";

interface ParliamentarySourceProps {
  type: string;
  reference: string;
  date: string;
  member?: string;
}

export function ParliamentarySource({
  type,
  reference,
  date,
  member,
}: ParliamentarySourceProps) {
  return (
    <div className="flex items-start gap-2 rounded-md border border-green-100 bg-green-50 px-3 py-2 text-sm">
      <Landmark className="mt-0.5 h-4 w-4 shrink-0 text-green-600" />
      <div className="min-w-0">
        <div className="font-medium text-green-900">{type}</div>
        <div className="text-green-700">{reference}</div>
        <div className="text-xs text-green-600">
          {date}
          {member && <> &middot; {member}</>}
        </div>
      </div>
    </div>
  );
}
