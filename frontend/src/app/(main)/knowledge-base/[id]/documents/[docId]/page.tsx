"use client";

/**
 * Document Detail Page — Metadata, processing status, and version history.
 */

import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@/lib/auth/auth-context";
import { ProcessingStatus } from "@/components/documents/processing-status";
import { ArrowLeft, FileText, Clock } from "lucide-react";

export default function DocumentDetailPage() {
  const params = useParams();
  const kbId = params.id as string;
  const docId = params.docId as string;
  const { api } = useAuth();

  const { data: doc } = useQuery({
    queryKey: ["document", kbId, docId],
    queryFn: () => api.documents.get(kbId, docId),
  });

  const { data: versions } = useQuery({
    queryKey: ["document-versions", kbId, docId],
    queryFn: () => api.documents.getVersions(kbId, docId),
  });

  if (!doc) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-neutral-600">Loading document...</div>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="border-b border-neutral-200 bg-white px-6 py-4">
        <div className="flex items-center gap-3">
          <a
            href={`/knowledge-base/${kbId}`}
            className="rounded p-1 text-neutral-400 hover:text-neutral-600"
          >
            <ArrowLeft className="h-5 w-5" />
          </a>
          <div>
            <h1 className="text-xl font-semibold text-neutral-900">{doc.name}</h1>
            <p className="text-sm text-neutral-500">
              Version {doc.version_number}
              {doc.mime_type && ` \u00b7 ${doc.mime_type}`}
              {doc.byte_size && ` \u00b7 ${(doc.byte_size / 1024).toFixed(0)} KB`}
            </p>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        <div className="mx-auto max-w-3xl space-y-8">
          {/* Processing Status */}
          <section>
            <h2 className="mb-3 text-lg font-semibold text-neutral-900">Processing Status</h2>
            <ProcessingStatus
              state={doc.processing_state}
              errorMessage={doc.last_error_message}
            />
          </section>

          {/* Metadata */}
          <section>
            <h2 className="mb-3 text-lg font-semibold text-neutral-900">Details</h2>
            <dl className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <dt className="text-neutral-500">Chunks</dt>
                <dd className="font-medium text-neutral-900">{doc.chunk_count}</dd>
              </div>
              <div>
                <dt className="text-neutral-500">Retries</dt>
                <dd className="font-medium text-neutral-900">{doc.retry_count}</dd>
              </div>
              <div>
                <dt className="text-neutral-500">Created</dt>
                <dd className="font-medium text-neutral-900">
                  {doc.created_at ? new Date(doc.created_at).toLocaleString() : "—"}
                </dd>
              </div>
              <div>
                <dt className="text-neutral-500">Updated</dt>
                <dd className="font-medium text-neutral-900">
                  {doc.updated_at ? new Date(doc.updated_at).toLocaleString() : "—"}
                </dd>
              </div>
              {doc.hash && (
                <div className="col-span-2">
                  <dt className="text-neutral-500">Hash</dt>
                  <dd className="font-mono text-xs text-neutral-700">{doc.hash}</dd>
                </div>
              )}
            </dl>
          </section>

          {/* Version History */}
          {versions && versions.length > 0 && (
            <section>
              <h2 className="mb-3 text-lg font-semibold text-neutral-900">Version History</h2>
              <div className="space-y-2">
                {versions.map((v) => (
                  <div
                    key={v.id}
                    className="flex items-center gap-3 rounded-md border border-neutral-200 px-4 py-3"
                  >
                    <Clock className="h-4 w-4 text-neutral-400" />
                    <div className="flex-1">
                      <div className="text-sm font-medium text-neutral-900">
                        Version {v.version_number}
                      </div>
                      <div className="text-xs text-neutral-500">
                        {v.created_at ? new Date(v.created_at).toLocaleString() : "—"}
                        {v.byte_size && ` \u00b7 ${(v.byte_size / 1024).toFixed(0)} KB`}
                      </div>
                    </div>
                    <span className="text-xs capitalize text-neutral-500">
                      {v.processing_state.replace(/_/g, " ")}
                    </span>
                  </div>
                ))}
              </div>
            </section>
          )}
        </div>
      </div>
    </div>
  );
}
