"use client";

/**
 * ConversationHeader — Title with inline rename, delete, and export actions.
 */

import { useState, useRef, useEffect } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth/auth-context";
import { Pencil, Trash2, Check, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { ConversationResponse } from "@/lib/types/conversations";

interface ConversationHeaderProps {
  conversation: ConversationResponse;
}

export function ConversationHeader({ conversation }: ConversationHeaderProps) {
  const { api } = useAuth();
  const router = useRouter();
  const queryClient = useQueryClient();

  const [isEditing, setIsEditing] = useState(false);
  const [title, setTitle] = useState(conversation.title || "");
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isEditing) inputRef.current?.focus();
  }, [isEditing]);

  const renameMutation = useMutation({
    mutationFn: (newTitle: string) =>
      api.conversations.update(conversation.id, { title: newTitle }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["conversation", conversation.id] });
      queryClient.invalidateQueries({ queryKey: ["conversations"] });
      setIsEditing(false);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () => api.conversations.delete(conversation.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["conversations"] });
      router.push("/conversations");
    },
  });

  const handleSave = () => {
    const trimmed = title.trim();
    if (trimmed && trimmed !== conversation.title) {
      renameMutation.mutate(trimmed);
    } else {
      setIsEditing(false);
      setTitle(conversation.title || "");
    }
  };

  return (
    <div className="flex items-center justify-between border-b border-neutral-200 bg-white px-6 py-4">
      <div className="flex items-center gap-2 min-w-0">
        {isEditing ? (
          <div className="flex items-center gap-1">
            <input
              ref={inputRef}
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") handleSave();
                if (e.key === "Escape") {
                  setIsEditing(false);
                  setTitle(conversation.title || "");
                }
              }}
              className="rounded border border-neutral-300 px-2 py-1 text-lg font-semibold text-neutral-900"
            />
            <button onClick={handleSave} className="rounded p-1 text-green-600 hover:bg-green-50">
              <Check className="h-4 w-4" />
            </button>
            <button
              onClick={() => {
                setIsEditing(false);
                setTitle(conversation.title || "");
              }}
              className="rounded p-1 text-neutral-400 hover:bg-neutral-100"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        ) : (
          <>
            <h1 className="truncate text-xl font-semibold text-neutral-900">
              {conversation.title || "New Conversation"}
            </h1>
            <button
              onClick={() => setIsEditing(true)}
              className="rounded p-1 text-neutral-400 hover:text-neutral-600 hover:bg-neutral-100"
              aria-label="Rename conversation"
            >
              <Pencil className="h-4 w-4" />
            </button>
          </>
        )}
      </div>

      <div className="flex items-center gap-1">
        {showDeleteConfirm ? (
          <div className="flex items-center gap-2 text-sm">
            <span className="text-red-600">Delete this conversation?</span>
            <Button
              variant="destructive"
              size="sm"
              onClick={() => deleteMutation.mutate()}
              disabled={deleteMutation.isPending}
            >
              Delete
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowDeleteConfirm(false)}
            >
              Cancel
            </Button>
          </div>
        ) : (
          <button
            onClick={() => setShowDeleteConfirm(true)}
            className="rounded p-1.5 text-neutral-400 hover:text-red-600 hover:bg-red-50"
            aria-label="Delete conversation"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        )}
      </div>
    </div>
  );
}
