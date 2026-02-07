"use client";

/**
 * Conversations Page — List of user's conversations
 */

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth/auth-context";
import { Button } from "@/components/ui/button";
import { Plus, MessageSquare } from "lucide-react";
import type { ConversationResponse } from "@/lib/types/conversations";

export default function ConversationsPage() {
  const { api } = useAuth();
  const router = useRouter();
  const [conversations, setConversations] = useState<ConversationResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Load conversations on mount
  useEffect(() => {
    const loadConversations = async () => {
      try {
        const page = await api.conversations.list({ page: 1, page_size: 50 });
        setConversations(page.items);
      } catch (error) {
        console.error("Failed to load conversations:", error);
      } finally {
        setIsLoading(false);
      }
    };

    loadConversations();
  }, [api]);

  // Create new conversation
  const handleCreateConversation = async () => {
    try {
      const newConv = await api.conversations.create({});
      router.push(`/conversations/${newConv.id}`);
    } catch (error) {
      console.error("Failed to create conversation:", error);
    }
  };

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-neutral-600">Loading conversations...</div>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-neutral-200 bg-white px-6 py-4">
        <h1 className="text-2xl font-bold text-neutral-900">Conversations</h1>
        <Button onClick={handleCreateConversation}>
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
            <Button onClick={handleCreateConversation} className="mt-6">
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

/**
 * Conversation Card Component
 */
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
      className="flex flex-col items-start rounded-lg border border-neutral-200 bg-white p-4 text-left transition-colors hover:border-brand-300 hover:bg-brand-50"
    >
      <div className="flex items-start gap-3">
        <MessageSquare className="h-5 w-5 text-brand-600" />
        <div className="flex-1 min-w-0">
          <h3 className="font-medium text-neutral-900 truncate">
            {conversation.title || "Untitled Conversation"}
          </h3>
          <p className="mt-1 text-sm text-neutral-500">
            {conversation.created_at ? new Date(conversation.created_at).toLocaleDateString() : ""}
          </p>
        </div>
      </div>
    </button>
  );
}
