/**
 * Message Bubble Component — Individual message display
 */

import { User, Bot } from "lucide-react";
import { cn } from "@/lib/utils/cn";
import type { Message } from "@/lib/api/types";

interface MessageBubbleProps {
  message: Message;
  isStreaming?: boolean;
}

export function MessageBubble({ message, isStreaming }: MessageBubbleProps) {
  const isUser = message.role === "user";

  return (
    <div
      className={cn(
        "flex gap-4",
        isUser && "flex-row-reverse",
      )}
    >
      {/* Avatar */}
      <div
        className={cn(
          "flex h-8 w-8 shrink-0 items-center justify-center rounded-full",
          isUser
            ? "bg-brand-600 text-white"
            : "bg-neutral-200 text-neutral-700",
        )}
      >
        {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
      </div>

      {/* Message Content */}
      <div className={cn("flex-1 space-y-2", isUser && "flex flex-col items-end")}>
        <div
          className={cn(
            "rounded-2xl px-4 py-3 max-w-[80%]",
            isUser
              ? "bg-brand-600 text-white"
              : "bg-white border border-neutral-200 text-neutral-900",
          )}
        >
          <div className="whitespace-pre-wrap break-words text-sm">
            {message.content}
            {isStreaming && (
              <span className="inline-block h-4 w-1 animate-pulse bg-current ml-1" />
            )}
          </div>
        </div>

        {/* Metadata */}
        {!isUser && message.confidence_level && (
          <div className="flex items-center gap-2 text-xs text-neutral-500">
            <ConfidenceBadge level={message.confidence_level} />
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * Confidence Badge Component
 */
function ConfidenceBadge({ level }: { level: "high" | "medium" | "low" }) {
  const colors = {
    high: "bg-confidence-high text-white",
    medium: "bg-confidence-medium text-neutral-900",
    low: "bg-confidence-low text-white",
  };

  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium",
        colors[level],
      )}
    >
      {level.charAt(0).toUpperCase() + level.slice(1)} Confidence
    </span>
  );
}
