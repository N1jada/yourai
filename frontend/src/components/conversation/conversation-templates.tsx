"use client";

/**
 * ConversationTemplates — Clickable template suggestions for new conversations.
 */

import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@/lib/auth/auth-context";
import { Sparkles } from "lucide-react";

interface ConversationTemplatesProps {
  onSelect: (content: string) => void;
}

export function ConversationTemplates({ onSelect }: ConversationTemplatesProps) {
  const { api } = useAuth();

  const { data: templates } = useQuery({
    queryKey: ["conversation-templates"],
    queryFn: () => api.templates.list(),
  });

  if (!templates || templates.length === 0) return null;

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 text-sm text-neutral-500">
        <Sparkles className="h-4 w-4" />
        <span>Suggested starting points</span>
      </div>
      <div className="grid gap-2 sm:grid-cols-2">
        {templates.map((template) => (
          <button
            key={template.id}
            onClick={() => onSelect(template.name)}
            className="rounded-lg border border-neutral-200 bg-white px-4 py-3 text-left text-sm text-neutral-700 transition-colors hover:border-neutral-300 hover:bg-neutral-50"
          >
            {template.name}
            {template.description && (
              <span className="mt-1 block text-xs text-neutral-400">
                {template.description}
              </span>
            )}
          </button>
        ))}
      </div>
    </div>
  );
}
