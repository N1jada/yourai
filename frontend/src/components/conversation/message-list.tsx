/**
 * Message List Component — Displays conversation messages with streaming
 */

import { useEffect, useRef } from "react";
import { MessageBubble } from "./message-bubble";
import type { Message } from "@/lib/api/types";

interface MessageListProps {
  messages: Message[];
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
            role: "assistant",
            content: streamingText,
            state: "streaming",
            created_at: new Date().toISOString(),
          } as Message}
          isStreaming
        />
      )}

      <div ref={bottomRef} />
    </div>
  );
}
