"use client";

/**
 * Knowledge Base Detail Page — Document table with upload and search.
 */

import { useState } from "react";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@/lib/auth/auth-context";
import { DocumentUpload } from "@/components/documents/document-upload";
import { ProcessingBadge } from "@/components/documents/processing-status";
import { SkeletonRow } from "@/components/ui/skeleton";
import { Search, ArrowLeft, FileText, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { DocumentResponse } from "@/lib/types/knowledge";

export default function KnowledgeBaseDetailPage() {
  const params = useParams();
  const kbId = params.id as string;
  const { api } = useAuth();
  const [showUpload, setShowUpload] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");

  const { data: kb } = useQuery({
    queryKey: ["knowledge-base", kbId],
    queryFn: () => api.knowledgeBases.get(kbId),
  });

  const { data: documentsPage, isLoading } = useQuery({
    queryKey: ["documents", kbId],
    queryFn: () => api.documents.list(kbId, { page: 1, page_size: 50 }),
  });

  const documents = documentsPage?.items ?? [];
  const filteredDocs = searchQuery
    ? documents.filter((d) =>
        d.name.toLowerCase().includes(searchQuery.toLowerCase()),
      )
    : documents;

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="border-b border-neutral-200 bg-white px-6 py-4">
        <div className="flex items-center gap-3">
          <a
            href="/knowledge-base"
            className="rounded p-1 text-neutral-400 hover:text-neutral-600"
          >
            <ArrowLeft className="h-5 w-5" />
          </a>
          <div>
            <h1 className="text-xl font-semibold text-neutral-900">
              {kb?.name || "Knowledge Base"}
            </h1>
            {kb && (
              <p className="text-sm capitalize text-neutral-500">
                {kb.category.replace(/_/g, " ")} &middot; {kb.document_count} documents
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Toolbar */}
      <div className="flex items-center gap-3 border-b border-neutral-100 bg-white px-6 py-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-400" />
          <Input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search documents..."
            className="pl-9"
          />
        </div>
        <Button onClick={() => setShowUpload(!showUpload)}>
          {showUpload ? "Hide Upload" : "Upload Documents"}
        </Button>
      </div>

      {/* Upload area */}
      {showUpload && (
        <div className="border-b border-neutral-100 bg-neutral-50 px-6 py-4">
          <DocumentUpload knowledgeBaseId={kbId} />
        </div>
      )}

      {/* Document table */}
      <div className="flex-1 overflow-y-auto">
        {isLoading ? (
          <div className="space-y-1">
            <SkeletonRow />
            <SkeletonRow />
            <SkeletonRow />
          </div>
        ) : filteredDocs.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12">
            <FileText className="h-12 w-12 text-neutral-400" />
            <p className="mt-4 text-neutral-600">
              {searchQuery ? "No documents match your search" : "No documents uploaded yet"}
            </p>
          </div>
        ) : (
          <table className="w-full">
            <thead className="border-b border-neutral-200 bg-neutral-50 text-left text-xs font-medium uppercase text-neutral-500">
              <tr>
                <th className="px-6 py-3">Name</th>
                <th className="px-6 py-3">Status</th>
                <th className="px-6 py-3">Size</th>
                <th className="px-6 py-3">Chunks</th>
                <th className="px-6 py-3">Updated</th>
                <th className="px-6 py-3 w-12" />
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-100">
              {filteredDocs.map((doc) => (
                <DocumentRow key={doc.id} doc={doc} kbId={kbId} />
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

function DocumentRow({ doc, kbId }: { doc: DocumentResponse; kbId: string }) {
  return (
    <tr className="hover:bg-neutral-50">
      <td className="px-6 py-3">
        <a
          href={`/knowledge-base/${kbId}/documents/${doc.id}`}
          className="font-medium text-neutral-900 hover:underline"
        >
          {doc.name}
        </a>
        {doc.mime_type && (
          <span className="ml-2 text-xs text-neutral-400">
            {doc.mime_type.split("/").pop()?.toUpperCase()}
          </span>
        )}
      </td>
      <td className="px-6 py-3">
        <ProcessingBadge state={doc.processing_state} />
      </td>
      <td className="px-6 py-3 text-sm text-neutral-600">
        {doc.byte_size ? `${(doc.byte_size / 1024).toFixed(0)} KB` : "—"}
      </td>
      <td className="px-6 py-3 text-sm text-neutral-600">{doc.chunk_count}</td>
      <td className="px-6 py-3 text-sm text-neutral-500">
        {doc.updated_at ? new Date(doc.updated_at).toLocaleDateString() : "—"}
      </td>
      <td className="px-6 py-3">
        <button className="rounded p-1 text-neutral-400 hover:text-red-600">
          <Trash2 className="h-4 w-4" />
        </button>
      </td>
    </tr>
  );
}
