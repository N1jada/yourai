/**
 * Message List Component — Displays conversation messages with streaming and scroll management.
 */

import { useEffect, useRef, useState, useCallback } from "react";
import { ArrowDown } from "lucide-react";
import { MessageBubble } from "./message-bubble";
import { AgentProgress } from "./agent-progress";
import { Button } from "../ui/button";
import type { MessageResponse } from "@/lib/types/conversations";
import type { ConfidenceLevel } from "@/lib/types/enums";

interface AgentStatus {
  name: string;
  status: "running" | "complete";
  taskDescription?: string;
  statusText?: string;
  durationMs?: number;
}

interface SourceData {
  type: "legal" | "case_law" | "company_policy" | "parliamentary";
  [key: string]: unknown;
}

interface MessageListProps {
  messages: MessageResponse[];
  streamingText?: string;
  isStreaming?: boolean;
  agents?: AgentStatus[];
  streamingConfidence?: { level: ConfidenceLevel; reason: string } | null;
  streamingSources?: SourceData[];
  /** Initial acknowledgement text before content arrives. */
  acknowledgement?: string | null;
}

export function MessageList({
  messages,
  streamingText,
  isStreaming,
  agents,
  streamingConfidence,
  streamingSources,
  acknowledgement,
}: MessageListProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const [isAtBottom, setIsAtBottom] = useState(true);

  const scrollToBottom = useCallback(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  // Track scroll position
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const handleScroll = () => {
      const { scrollTop, scrollHeight, clientHeight } = container;
      setIsAtBottom(scrollHeight - scrollTop - clientHeight < 50);
    };

    container.addEventListener("scroll", handleScroll);
    return () => container.removeEventListener("scroll", handleScroll);
  }, []);

  // Auto-scroll when at bottom and new content arrives
  useEffect(() => {
    if (isAtBottom) {
      scrollToBottom();
    }
  }, [messages, streamingText, isAtBottom, scrollToBottom]);

  return (
    <div ref={containerRef} className="relative h-full overflow-y-auto">
      <div
        className="mx-auto max-w-4xl px-4 py-6 space-y-6"
        role="log"
        aria-label="Conversation"
      >
        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}

        {/* Streaming acknowledgement before content */}
        {isStreaming && !streamingText && acknowledgement && (
          <div className="flex gap-4" aria-live="polite">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-neutral-200 text-neutral-700" aria-hidden="true">
              <span className="h-4 w-4 animate-pulse rounded-full bg-neutral-400" />
            </div>
            <div className="text-sm italic text-neutral-500">
              {acknowledgement}
            </div>
          </div>
        )}

        {/* Agent progress chips */}
        {isStreaming && agents && agents.length > 0 && (
          <AgentProgress agents={agents} className="ml-12" />
        )}

        {/* Streaming message */}
        {isStreaming && streamingText && (
          <div aria-live="polite">
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
                confidence_level: streamingConfidence?.level ?? null,
                verification_result: null,
                feedback: null,
                created_at: new Date().toISOString(),
                updated_at: null,
              }}
              isStreaming
              sources={streamingSources}
            />
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Scroll to bottom button */}
      {!isAtBottom && (
        <div className="sticky bottom-4 flex justify-center">
          <Button
            variant="outline"
            size="sm"
            onClick={scrollToBottom}
            className="rounded-full shadow-md"
            aria-label="Scroll to latest messages"
          >
            <ArrowDown className="mr-1 h-4 w-4" />
            New messages
          </Button>
        </div>
      )}
    </div>
  );
}
