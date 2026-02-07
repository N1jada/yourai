"use client";

/**
 * Conversation Page — Chat interface with full SSE streaming and TanStack Query.
 */

import { useState, useEffect, useRef, useCallback } from "react";
import { useParams } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/lib/auth/auth-context";
import { useStreamingStore } from "@/stores/streaming-store";
import { SSEClient } from "@/lib/streaming/sse-client";
import { MessageList } from "@/components/conversation/message-list";
import { ChatInput } from "@/components/conversation/chat-input";
import { ConversationHeader } from "@/components/conversation/conversation-header";
import { ConversationTemplates } from "@/components/conversation/conversation-templates";
import { PersonaSelector } from "@/components/personas/persona-selector";
import { Button } from "@/components/ui/button";
import { SkeletonMessage } from "@/components/ui/skeleton";
import { Square } from "lucide-react";
import type { SSEEventEnvelope } from "@/lib/streaming/sse-client";
import type { AnySSEEvent } from "@/lib/types/stream";

export default function ConversationPage() {
  const params = useParams();
  const conversationId = params.id as string;
  const { api } = useAuth();
  const queryClient = useQueryClient();

  const [isSending, setIsSending] = useState(false);
  const [acknowledgement, setAcknowledgement] = useState<string | null>(null);
  const sseClient = useRef<SSEClient | null>(null);

  const streaming = useStreamingStore();

  // Fetch conversation
  const { data: conversation } = useQuery({
    queryKey: ["conversation", conversationId],
    queryFn: () => api.conversations.get(conversationId),
  });

  // Fetch messages
  const { data: messagesPage, isLoading: messagesLoading } = useQuery({
    queryKey: ["messages", conversationId],
    queryFn: () => api.messages.list(conversationId, { page: 1, page_size: 100 }),
  });

  const messages = messagesPage?.items ?? [];

  // Handle SSE events — dispatch to streaming store
  const handleSSEEvent = useCallback(
    (envelope: SSEEventEnvelope) => {
      const data = envelope.data as AnySSEEvent;

      switch (data.event_type) {
        // Agent lifecycle
        case "agent_start":
          streaming.addAgent(data.agent_name, data.task_description);
          break;
        case "agent_progress":
          streaming.updateAgent(data.agent_name, data.status_text);
          break;
        case "agent_complete":
          streaming.completeAgent(data.agent_name, data.duration_ms);
          break;

        // Content
        case "content_delta":
          setAcknowledgement(null);
          streaming.appendText(data.text);
          break;

        // Sources
        case "legal_source":
          streaming.addSource({
            type: "legal",
            act_name: data.act_name,
            section: data.section,
            uri: data.uri,
            verification_status: data.verification_status,
          });
          break;
        case "case_law_source":
          streaming.addSource({
            type: "case_law",
            case_name: data.case_name,
            citation: data.citation,
            court: data.court,
            date: data.date,
          });
          break;
        case "company_policy_source":
          streaming.addSource({
            type: "company_policy",
            document_name: data.document_name,
            section: data.section,
          });
          break;
        case "parliamentary_source":
          streaming.addSource({
            type: "parliamentary",
            parliamentary_type: data.type,
            reference: data.reference,
            date: data.date,
            member: data.member,
          });
          break;

        // Quality
        case "confidence_update":
          streaming.setConfidence(data.level, data.reason);
          break;
        case "verification_result":
          streaming.setVerificationResult({
            citationsChecked: data.citations_checked,
            citationsVerified: data.citations_verified,
            issues: data.issues,
          });
          break;

        // Lifecycle
        case "message_complete":
          queryClient.invalidateQueries({
            queryKey: ["messages", conversationId],
          });
          streaming.reset();
          setIsSending(false);
          setAcknowledgement(null);
          break;

        case "conversation_state":
          queryClient.invalidateQueries({
            queryKey: ["conversation", conversationId],
          });
          break;

        case "conversation_cancelled":
          streaming.reset();
          setIsSending(false);
          setAcknowledgement(null);
          break;

        case "error":
          console.error("Stream error:", data.message);
          if (!data.recoverable) {
            streaming.reset();
            setIsSending(false);
            setAcknowledgement(null);
          }
          break;

        // User push events
        case "conversation_title_updated":
          queryClient.setQueryData(
            ["conversation", conversationId],
            (prev: typeof conversation) =>
              prev ? { ...prev, title: data.title } : prev,
          );
          break;

        // Ignore annotation, usage_metrics, message_state etc. for now
        default:
          break;
      }
    },
    [conversationId, queryClient, streaming, conversation],
  );

  // Connect SSE
  useEffect(() => {
    sseClient.current = new SSEClient();

    const cleanup = sseClient.current.connect(
      conversationId,
      handleSSEEvent,
      (error) => console.error("SSE error:", error),
    );

    return () => {
      cleanup();
      sseClient.current = null;
    };
  }, [conversationId, handleSSEEvent]);

  // Send message
  const handleSendMessage = async (content: string) => {
    setIsSending(true);
    streaming.startStreaming(conversationId);

    // Show acknowledgement immediately
    const preview = content.length > 60 ? content.slice(0, 60) + "..." : content;
    setAcknowledgement(`Analysing your question about "${preview}"...`);

    try {
      await api.messages.send(conversationId, { content });
      // Optimistically add user message to list
      queryClient.invalidateQueries({
        queryKey: ["messages", conversationId],
      });
    } catch (error) {
      console.error("Failed to send message:", error);
      setIsSending(false);
      streaming.reset();
      setAcknowledgement(null);
    }
  };

  // Cancel generation
  const handleCancel = async () => {
    try {
      await api.conversations.cancel(conversationId);
    } catch (error) {
      console.error("Failed to cancel:", error);
    }
    streaming.reset();
    setIsSending(false);
    setAcknowledgement(null);
  };

  if (messagesLoading) {
    return (
      <div className="flex h-full flex-col">
        <div className="border-b border-neutral-200 bg-white px-6 py-4">
          <div className="h-7 w-48 animate-pulse rounded bg-neutral-200" />
        </div>
        <div className="flex-1 overflow-y-auto">
          <div className="mx-auto max-w-4xl space-y-6 p-6">
            <SkeletonMessage />
            <SkeletonMessage />
            <SkeletonMessage />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      {conversation && <ConversationHeader conversation={conversation} />}

      {/* Message List */}
      <div className="flex-1 overflow-hidden">
        <MessageList
          messages={messages}
          streamingText={streaming.streamingText}
          isStreaming={isSending}
          agents={streaming.agents}
          streamingConfidence={streaming.confidence}
          streamingSources={streaming.sources as Array<{
            type: "legal" | "case_law" | "company_policy" | "parliamentary";
            [key: string]: unknown;
          }>}
          acknowledgement={acknowledgement}
        />
      </div>

      {/* Templates for empty conversations */}
      {messages.length === 0 && !isSending && (
        <div className="mx-auto max-w-4xl px-4 pb-4">
          <ConversationTemplates onSelect={handleSendMessage} />
        </div>
      )}

      {/* Chat Input + Cancel */}
      <div className="border-t border-neutral-200 bg-white p-4">
        {isSending ? (
          <div className="flex items-center justify-center gap-3">
            <span className="text-sm text-neutral-500">Generating response...</span>
            <Button variant="outline" size="sm" onClick={handleCancel}>
              <Square className="mr-1 h-3 w-3" />
              Stop
            </Button>
          </div>
        ) : (
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <PersonaSelector />
            </div>
            <ChatInput
              onSend={handleSendMessage}
              disabled={isSending}
              placeholder="Ask a compliance question..."
            />
          </div>
        )}
      </div>
    </div>
  );
}
