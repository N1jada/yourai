"use client";

/**
 * Persona Management Page — CRUD for AI personas.
 */

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/lib/auth/auth-context";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { SkeletonCard } from "@/components/ui/skeleton";
import { Bot, Plus, Pencil, Trash2, Copy, X } from "lucide-react";
import type { PersonaResponse } from "@/lib/types/personas";
import type { CreatePersona, UpdatePersona } from "@/lib/types/requests";

export default function PersonasPage() {
  const { api } = useAuth();
  const queryClient = useQueryClient();
  const [editingId, setEditingId] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["admin-personas"],
    queryFn: () => api.personas.list({ page: 1, page_size: 50 }),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.personas.delete(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin-personas"] }),
  });

  const duplicateMutation = useMutation({
    mutationFn: (id: string) => api.personas.duplicate(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin-personas"] }),
  });

  const personas = data?.items ?? [];

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
        <h2 className="text-lg font-semibold text-neutral-900">AI Personas</h2>
        <Button onClick={() => setShowCreate(!showCreate)}>
          <Plus className="mr-2 h-4 w-4" />
          New Persona
        </Button>
      </div>

      {showCreate && (
        <div className="mb-6 rounded-lg border border-neutral-200 bg-white p-5">
          <PersonaForm
            onSubmit={() => {
              setShowCreate(false);
              queryClient.invalidateQueries({ queryKey: ["admin-personas"] });
            }}
            onCancel={() => setShowCreate(false)}
          />
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2">
        {personas.map((persona) => (
          <div
            key={persona.id}
            className="rounded-lg border border-neutral-200 bg-white p-5"
          >
            {editingId === persona.id ? (
              <PersonaForm
                persona={persona}
                onSubmit={() => {
                  setEditingId(null);
                  queryClient.invalidateQueries({ queryKey: ["admin-personas"] });
                }}
                onCancel={() => setEditingId(null)}
              />
            ) : (
              <>
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2">
                    <Bot className="h-5 w-5 text-blue-500" />
                    <h3 className="font-semibold text-neutral-900">{persona.name}</h3>
                  </div>
                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => duplicateMutation.mutate(persona.id)}
                      className="rounded p-1 text-neutral-400 hover:text-neutral-600"
                      title="Duplicate"
                    >
                      <Copy className="h-4 w-4" />
                    </button>
                    <button
                      onClick={() => setEditingId(persona.id)}
                      className="rounded p-1 text-neutral-400 hover:text-neutral-600"
                      title="Edit"
                    >
                      <Pencil className="h-4 w-4" />
                    </button>
                    <button
                      onClick={() => {
                        if (confirm("Delete this persona?"))
                          deleteMutation.mutate(persona.id);
                      }}
                      className="rounded p-1 text-neutral-400 hover:text-red-600"
                      title="Delete"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
                {persona.description && (
                  <p className="mt-2 text-sm text-neutral-600">{persona.description}</p>
                )}
              </>
            )}
          </div>
        ))}
      </div>

      {personas.length === 0 && !showCreate && (
        <div className="flex flex-col items-center py-12 text-neutral-500">
          <Bot className="h-12 w-12" />
          <p className="mt-4">No personas configured</p>
        </div>
      )}
    </div>
  );
}

function PersonaForm({
  persona,
  onSubmit,
  onCancel,
}: {
  persona?: PersonaResponse;
  onSubmit: () => void;
  onCancel: () => void;
}) {
  const { api } = useAuth();
  const [name, setName] = useState(persona?.name ?? "");
  const [description, setDescription] = useState(persona?.description ?? "");
  const [instructions, setInstructions] = useState(
    persona?.system_instructions ?? "",
  );

  const createMutation = useMutation({
    mutationFn: (data: CreatePersona) => api.personas.create(data),
    onSuccess: onSubmit,
  });

  const updateMutation = useMutation({
    mutationFn: (data: UpdatePersona) =>
      api.personas.update(persona!.id, data),
    onSuccess: onSubmit,
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    const data = {
      name: name.trim(),
      description: description.trim() || undefined,
      system_instructions: instructions.trim() || undefined,
    };

    if (persona) {
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
        <Input value={name} onChange={(e) => setName(e.target.value)} required />
      </div>
      <div>
        <label className="text-xs text-neutral-500">Description</label>
        <Input
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="What this persona focuses on..."
        />
      </div>
      <div>
        <label className="text-xs text-neutral-500">System Instructions</label>
        <Textarea
          value={instructions}
          onChange={(e) => setInstructions(e.target.value)}
          placeholder="Instructions that modify AI behaviour..."
          rows={4}
        />
      </div>
      <div className="flex justify-end gap-2">
        <Button type="button" variant="outline" onClick={onCancel}>
          <X className="mr-1 h-4 w-4" />
          Cancel
        </Button>
        <Button type="submit" disabled={isPending}>
          {persona ? "Update" : "Create"} Persona
        </Button>
      </div>
    </form>
  );
}
