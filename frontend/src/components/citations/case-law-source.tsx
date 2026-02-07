/**
 * CaseLawSource — Displays a case law citation.
 */

import { Scale } from "lucide-react";

interface CaseLawSourceProps {
  caseName: string;
  citation: string;
  court: string;
  date: string;
}

export function CaseLawSource({
  caseName,
  citation,
  court,
  date,
}: CaseLawSourceProps) {
  return (
    <div className="flex items-start gap-2 rounded-md border border-purple-100 bg-purple-50 px-3 py-2 text-sm">
      <Scale className="mt-0.5 h-4 w-4 shrink-0 text-purple-500" />
      <div className="min-w-0">
        <div className="font-medium text-purple-900">{caseName}</div>
        <div className="text-purple-700">{citation}</div>
        <div className="text-xs text-purple-600">
          {court} &middot; {date}
        </div>
      </div>
    </div>
  );
}
