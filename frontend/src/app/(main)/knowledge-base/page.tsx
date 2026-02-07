"use client";

/**
 * Knowledge Base List Page — Shows all knowledge bases with category badges.
 */

import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@/lib/auth/auth-context";
import { SkeletonCard } from "@/components/ui/skeleton";
import { FileText, Database } from "lucide-react";
import { cn } from "@/lib/utils/cn";
import type { KnowledgeBaseResponse } from "@/lib/types/knowledge";
import type { KnowledgeBaseCategory } from "@/lib/types/enums";

const categoryColors: Record<KnowledgeBaseCategory, string> = {
  legislation: "bg-blue-100 text-blue-700",
  case_law: "bg-purple-100 text-purple-700",
  explanatory_notes: "bg-cyan-100 text-cyan-700",
  amendments: "bg-orange-100 text-orange-700",
  company_policy: "bg-amber-100 text-amber-700",
  sector_knowledge: "bg-green-100 text-green-700",
  parliamentary: "bg-teal-100 text-teal-700",
};

export default function KnowledgeBasePage() {
  const { api } = useAuth();
  const router = useRouter();

  const { data, isLoading } = useQuery({
    queryKey: ["knowledge-bases"],
    queryFn: () => api.knowledgeBases.list({ page: 1, page_size: 50 }),
  });

  const knowledgeBases = data?.items ?? [];

  if (isLoading) {
    return (
      <div className="flex h-full flex-col">
        <div className="border-b border-neutral-200 bg-white px-6 py-4">
          <div className="h-8 w-48 animate-pulse rounded bg-neutral-200" />
        </div>
        <div className="flex-1 overflow-y-auto p-6">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-neutral-200 bg-white px-6 py-4">
        <h1 className="text-2xl font-bold text-neutral-900">Knowledge Base</h1>
        <p className="mt-1 text-sm text-neutral-500">
          Manage your organisation&apos;s document collections
        </p>
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        {knowledgeBases.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12">
            <Database className="h-12 w-12 text-neutral-400" />
            <p className="mt-4 text-neutral-600">No knowledge bases configured</p>
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {knowledgeBases.map((kb) => (
              <KBCard
                key={kb.id}
                kb={kb}
                onClick={() => router.push(`/knowledge-base/${kb.id}`)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function KBCard({
  kb,
  onClick,
}: {
  kb: KnowledgeBaseResponse;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="flex flex-col items-start rounded-lg border border-neutral-200 bg-white p-5 text-left transition-colors hover:border-neutral-300 hover:bg-neutral-50"
    >
      <div className="flex w-full items-start justify-between">
        <FileText className="h-6 w-6 text-neutral-500" />
        <span
          className={cn(
            "rounded-full px-2 py-0.5 text-xs font-medium capitalize",
            categoryColors[kb.category] || "bg-neutral-100 text-neutral-600",
          )}
        >
          {kb.category.replace(/_/g, " ")}
        </span>
      </div>
      <h3 className="mt-3 font-semibold text-neutral-900">{kb.name}</h3>
      <div className="mt-2 flex items-center gap-3 text-xs text-neutral-500">
        <span>{kb.document_count} documents</span>
        <span>{kb.ready_document_count} ready</span>
      </div>
      <div className="mt-1 text-xs capitalize text-neutral-400">
        {kb.source_type.replace(/_/g, " ")}
      </div>
    </button>
  );
}
