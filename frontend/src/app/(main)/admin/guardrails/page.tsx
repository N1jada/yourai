"use client";

/**
 * Guardrail Management Page — CRUD for AI safety guardrails.
 */

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/lib/auth/auth-context";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { SkeletonCard } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils/cn";
import { Shield, Plus, Pencil, Trash2, X } from "lucide-react";
import type { GuardrailResponse } from "@/lib/types/guardrails";
import type { GuardrailStatus } from "@/lib/types/enums";
import type { CreateGuardrail, UpdateGuardrail } from "@/lib/types/requests";

const statusColors: Record<GuardrailStatus, string> = {
  creating: "bg-blue-100 text-blue-700",
  updating: "bg-blue-100 text-blue-700",
  versioning: "bg-amber-100 text-amber-700",
  ready: "bg-green-100 text-green-700",
  failed: "bg-red-100 text-red-700",
  deleting: "bg-neutral-100 text-neutral-600",
};

export default function GuardrailsPage() {
  const { api } = useAuth();
  const queryClient = useQueryClient();
  const [editingId, setEditingId] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["admin-guardrails"],
    queryFn: () => api.guardrails.list({ page: 1, page_size: 50 }),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.guardrails.delete(id),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["admin-guardrails"] }),
  });

  const guardrails = data?.items ?? [];

  if (isLoading) {
    return (
      <div className="overflow-y-auto p-6">
        <div className="grid gap-4 sm:grid-cols-2">
          <SkeletonCard />
          <SkeletonCard />
        </div>
      </div>
    );
  }

  return (
    <div className="overflow-y-auto p-6">
      <div className="mb-6 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-neutral-900">
          AI Guardrails
        </h2>
        <Button onClick={() => setShowCreate(!showCreate)}>
          <Plus className="mr-2 h-4 w-4" />
          New Guardrail
        </Button>
      </div>

      {showCreate && (
        <div className="mb-6 rounded-lg border border-neutral-200 bg-white p-5">
          <GuardrailForm
            onSubmit={() => {
              setShowCreate(false);
              queryClient.invalidateQueries({
                queryKey: ["admin-guardrails"],
              });
            }}
            onCancel={() => setShowCreate(false)}
          />
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2">
        {guardrails.map((guardrail) => (
          <div
            key={guardrail.id}
            className="rounded-lg border border-neutral-200 bg-white p-5"
          >
            {editingId === guardrail.id ? (
              <GuardrailForm
                guardrail={guardrail}
                onSubmit={() => {
                  setEditingId(null);
                  queryClient.invalidateQueries({
                    queryKey: ["admin-guardrails"],
                  });
                }}
                onCancel={() => setEditingId(null)}
              />
            ) : (
              <>
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2">
                    <Shield className="h-5 w-5 text-amber-500" />
                    <h3 className="font-semibold text-neutral-900">
                      {guardrail.name}
                    </h3>
                  </div>
                  <div className="flex items-center gap-1">
                    <span
                      className={cn(
                        "rounded-full px-2 py-0.5 text-xs font-medium capitalize",
                        statusColors[guardrail.status],
                      )}
                    >
                      {guardrail.status}
                    </span>
                    <button
                      onClick={() => setEditingId(guardrail.id)}
                      className="rounded p-1 text-neutral-400 hover:text-neutral-600"
                      title="Edit"
                    >
                      <Pencil className="h-4 w-4" />
                    </button>
                    <button
                      onClick={() => {
                        if (confirm("Delete this guardrail?"))
                          deleteMutation.mutate(guardrail.id);
                      }}
                      className="rounded p-1 text-neutral-400 hover:text-red-600"
                      title="Delete"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
                {guardrail.description && (
                  <p className="mt-2 text-sm text-neutral-600">
                    {guardrail.description}
                  </p>
                )}
                {guardrail.configuration_rules &&
                  Object.keys(guardrail.configuration_rules).length > 0 && (
                    <div className="mt-3 rounded border border-neutral-100 bg-neutral-50 p-3">
                      <p className="mb-1 text-xs font-medium text-neutral-500">
                        Configuration Rules
                      </p>
                      <pre className="text-xs text-neutral-700">
                        {JSON.stringify(
                          guardrail.configuration_rules,
                          null,
                          2,
                        )}
                      </pre>
                    </div>
                  )}
              </>
            )}
          </div>
        ))}
      </div>

      {guardrails.length === 0 && !showCreate && (
        <div className="flex flex-col items-center py-12 text-neutral-500">
          <Shield className="h-12 w-12" />
          <p className="mt-4">No guardrails configured</p>
        </div>
      )}
    </div>
  );
}

function GuardrailForm({
  guardrail,
  onSubmit,
  onCancel,
}: {
  guardrail?: GuardrailResponse;
  onSubmit: () => void;
  onCancel: () => void;
}) {
  const { api } = useAuth();
  const [name, setName] = useState(guardrail?.name ?? "");
  const [description, setDescription] = useState(
    guardrail?.description ?? "",
  );
  const [rulesJson, setRulesJson] = useState(
    guardrail?.configuration_rules
      ? JSON.stringify(guardrail.configuration_rules, null, 2)
      : "",
  );

  const createMutation = useMutation({
    mutationFn: (data: CreateGuardrail) => api.guardrails.create(data),
    onSuccess: onSubmit,
  });

  const updateMutation = useMutation({
    mutationFn: (data: UpdateGuardrail) =>
      api.guardrails.update(guardrail!.id, data),
    onSuccess: onSubmit,
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    let parsedRules: Record<string, unknown> | undefined;
    if (rulesJson.trim()) {
      try {
        parsedRules = JSON.parse(rulesJson.trim()) as Record<string, unknown>;
      } catch {
        return; // invalid JSON — don't submit
      }
    }

    const data = {
      name: name.trim(),
      description: description.trim() || undefined,
      configuration_rules: parsedRules,
    };

    if (guardrail) {
      updateMutation.mutate(data);
    } else {
      createMutation.mutate(data);
    }
  };

  const isPending = createMutation.isPending || updateMutation.isPending;

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <div>
        <label className="text-xs text-neutral-500">Name</label>
        <Input
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
        />
      </div>
      <div>
        <label className="text-xs text-neutral-500">Description</label>
        <Input
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="What this guardrail enforces..."
        />
      </div>
      <div>
        <label className="text-xs text-neutral-500">
          Configuration Rules (JSON)
        </label>
        <Textarea
          value={rulesJson}
          onChange={(e) => setRulesJson(e.target.value)}
          placeholder='{"max_tokens": 4096, "blocked_topics": []}'
          rows={4}
          className="font-mono text-xs"
        />
      </div>
      <div className="flex justify-end gap-2">
        <Button type="button" variant="outline" onClick={onCancel}>
          <X className="mr-1 h-4 w-4" />
          Cancel
        </Button>
        <Button type="submit" disabled={isPending}>
          {guardrail ? "Update" : "Create"} Guardrail
        </Button>
      </div>
    </form>
  );
}
