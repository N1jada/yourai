/**
 * CompanyPolicySource — Displays an internal policy document citation.
 */

import { FileText } from "lucide-react";

interface CompanyPolicySourceProps {
  documentName: string;
  section: string;
}

export function CompanyPolicySource({
  documentName,
  section,
}: CompanyPolicySourceProps) {
  return (
    <div className="flex items-start gap-2 rounded-md border border-amber-100 bg-amber-50 px-3 py-2 text-sm">
      <FileText className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
      <div className="min-w-0">
        <div className="font-medium text-amber-900">{documentName}</div>
        <div className="text-amber-700">Section: {section}</div>
      </div>
    </div>
  );
}
