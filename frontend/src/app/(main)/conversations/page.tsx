"use client";

/**
 * Conversations Page — List of user's conversations with TanStack Query.
 */

import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/lib/auth/auth-context";
import { Button } from "@/components/ui/button";
import { SkeletonCard } from "@/components/ui/skeleton";
import { Plus, MessageSquare } from "lucide-react";
import type { ConversationResponse } from "@/lib/types/conversations";

export default function ConversationsPage() {
  const { api } = useAuth();
  const router = useRouter();
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["conversations"],
    queryFn: () => api.conversations.list({ page: 1, page_size: 50 }),
  });

  const createMutation = useMutation({
    mutationFn: () => api.conversations.create({}),
    onSuccess: (newConv) => {
      queryClient.invalidateQueries({ queryKey: ["conversations"] });
      router.push(`/conversations/${newConv.id}`);
    },
  });

  const conversations = data?.items ?? [];

  if (isLoading) {
    return (
      <div className="flex h-full flex-col">
        <div className="flex items-center justify-between border-b border-neutral-200 bg-white px-6 py-4">
          <div className="h-8 w-48 animate-pulse rounded bg-neutral-200" />
          <div className="h-10 w-40 animate-pulse rounded bg-neutral-200" />
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
      {/* Header */}
      <div className="flex items-center justify-between border-b border-neutral-200 bg-white px-6 py-4">
        <h1 className="text-2xl font-bold text-neutral-900">Conversations</h1>
        <Button
          onClick={() => createMutation.mutate()}
          disabled={createMutation.isPending}
        >
          <Plus className="mr-2 h-4 w-4" />
          New Conversation
        </Button>
      </div>

      {/* Conversation List */}
      <div className="flex-1 overflow-y-auto p-6">
        {conversations.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12">
            <MessageSquare className="h-12 w-12 text-neutral-400" />
            <p className="mt-4 text-neutral-600">No conversations yet</p>
            <p className="mt-2 text-sm text-neutral-500">
              Start a new conversation to get help with compliance questions
            </p>
            <Button
              onClick={() => createMutation.mutate()}
              disabled={createMutation.isPending}
              className="mt-6"
            >
              <Plus className="mr-2 h-4 w-4" />
              Start Conversation
            </Button>
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {conversations.map((conv) => (
              <ConversationCard
                key={conv.id}
                conversation={conv}
                onClick={() => router.push(`/conversations/${conv.id}`)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function ConversationCard({
  conversation,
  onClick,
}: {
  conversation: ConversationResponse;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="flex flex-col items-start rounded-lg border border-neutral-200 bg-white p-4 text-left transition-colors hover:border-neutral-300 hover:bg-neutral-50"
    >
      <div className="flex items-start gap-3">
        <MessageSquare className="h-5 w-5 text-neutral-600" />
        <div className="flex-1 min-w-0">
          <h3 className="font-medium text-neutral-900 truncate">
            {conversation.title || "Untitled Conversation"}
          </h3>
          <div className="mt-1 flex items-center gap-2 text-xs text-neutral-500">
            <span>
              {conversation.message_count} message{conversation.message_count !== 1 ? "s" : ""}
            </span>
            {conversation.created_at && (
              <>
                <span>&middot;</span>
                <span>{new Date(conversation.created_at).toLocaleDateString()}</span>
              </>
            )}
          </div>
        </div>
      </div>
    </button>
  );
}
