"use client";

/**
 * Conversation Page — Chat interface with message list and input
 */

import { useState, useEffect, useRef } from "react";
import { useParams } from "next/navigation";
import { useAuth } from "@/lib/auth/auth-context";
import { SSEClient } from "@/lib/streaming/sse-client";
import { MessageList } from "@/components/conversation/message-list";
import { ChatInput } from "@/components/conversation/chat-input";
import type { Message, Conversation } from "@/lib/api/types";
import type { SSEEvent } from "@/lib/streaming/sse-client";

export default function ConversationPage() {
  const params = useParams();
  const conversationId = params.id as string;
  const { api } = useAuth();

  const [conversation, setConversation] = useState<Conversation | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [streamingText, setStreamingText] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isSending, setIsSending] = useState(false);

  const sseClient = useRef<SSEClient | null>(null);

  // Load conversation and messages
  useEffect(() => {
    const load = async () => {
      try {
        const [conv, msgPage] = await Promise.all([
          api.conversations.get(conversationId),
          api.messages.list(conversationId, { page: 1, page_size: 100 }),
        ]);

        setConversation(conv);
        setMessages(msgPage.items);
      } catch (error) {
        console.error("Failed to load conversation:", error);
      } finally {
        setIsLoading(false);
      }
    };

    load();
  }, [conversationId, api]);

  // Connect to SSE stream
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
  }, [conversationId]);

  // Handle SSE events
  const handleSSEEvent = (event: SSEEvent) => {
    switch (event.event) {
      case "content_delta":
        setStreamingText((prev) => prev + event.data.text);
        break;

      case "message_complete":
        // Reload messages when complete
        api.messages.list(conversationId, { page: 1, page_size: 100 })
          .then((page) => {
            setMessages(page.items);
            setStreamingText("");
            setIsSending(false);
          });
        break;

      case "conversation_title_updated":
        setConversation((prev) =>
          prev ? { ...prev, title: event.data.title } : null,
        );
        break;

      case "error":
        console.error("Agent error:", event.data);
        setIsSending(false);
        setStreamingText("");
        break;
    }
  };

  // Send message
  const handleSendMessage = async (content: string) => {
    setIsSending(true);
    setStreamingText("");

    try {
      await api.messages.send(conversationId, { content });
      // SSE events will handle adding the response
    } catch (error) {
      console.error("Failed to send message:", error);
      setIsSending(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-neutral-600">Loading...</div>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="border-b border-neutral-200 bg-white px-6 py-4">
        <h1 className="text-xl font-semibold text-neutral-900">
          {conversation?.title || "New Conversation"}
        </h1>
      </div>

      {/* Message List */}
      <div className="flex-1 overflow-y-auto">
        <MessageList
          messages={messages}
          streamingText={streamingText}
          isStreaming={isSending && streamingText.length > 0}
        />
      </div>

      {/* Chat Input */}
      <div className="border-t border-neutral-200 bg-white p-4">
        <ChatInput
          onSend={handleSendMessage}
          disabled={isSending}
          placeholder="Ask a compliance question..."
        />
      </div>
    </div>
  );
}
