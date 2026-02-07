/**
 * Message List Component — Displays conversation messages with streaming
 */

import { useEffect, useRef } from "react";
import { MessageBubble } from "./message-bubble";
import type { MessageResponse } from "@/lib/types/conversations";

interface MessageListProps {
  messages: MessageResponse[];
  streamingText?: string;
  isStreaming?: boolean;
}

export function MessageList({ messages, streamingText, isStreaming }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingText]);

  return (
    <div className="mx-auto max-w-4xl px-4 py-6 space-y-6">
      {messages.map((message) => (
        <MessageBubble key={message.id} message={message} />
      ))}

      {/* Streaming message */}
      {isStreaming && streamingText && (
        <MessageBubble
          message={{
            id: "streaming",
            tenant_id: "",
            conversation_id: "",
            request_id: null,
            role: "assistant",
            content: streamingText,
            state: "pending",
            metadata_: {},
            file_attachments: [],
            confidence_level: null,
            verification_result: null,
            feedback: null,
            created_at: new Date().toISOString(),
            updated_at: null,
          }}
          isStreaming
        />
      )}

      <div ref={bottomRef} />
    </div>
  );
}
