/**
 * Message Bubble Component — Individual message display with citations and confidence.
 */

import { User, Bot } from "lucide-react";
import { cn } from "@/lib/utils/cn";
import { ConfidenceIndicator } from "@/components/confidence/confidence-indicator";
import { FeedbackButtons } from "./feedback-buttons";
import {
  LegalSource,
  CaseLawSource,
  CompanyPolicySource,
  ParliamentarySource,
} from "@/components/citations";
import type { MessageResponse } from "@/lib/types/conversations";
import type { ConfidenceLevel, VerificationStatus } from "@/lib/types/enums";

interface SourceData {
  type: "legal" | "case_law" | "company_policy" | "parliamentary";
  [key: string]: unknown;
}

interface MessageBubbleProps {
  message: MessageResponse;
  isStreaming?: boolean;
  /** Sources collected during streaming. */
  sources?: SourceData[];
}

export function MessageBubble({ message, isStreaming, sources }: MessageBubbleProps) {
  const isUser = message.role === "user";

  // Extract sources from message metadata if not provided via props
  const displaySources: SourceData[] =
    sources || (message.metadata_?.sources as SourceData[]) || [];

  return (
    <div
      className={cn("flex gap-4", isUser && "flex-row-reverse")}
      role="article"
      aria-label={`${isUser ? "You" : "Assistant"} said`}
    >
      {/* Avatar */}
      <div
        className={cn(
          "flex h-8 w-8 shrink-0 items-center justify-center rounded-full",
          isUser
            ? "bg-neutral-800 text-white"
            : "bg-neutral-200 text-neutral-700",
        )}
        aria-hidden="true"
      >
        {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
      </div>

      {/* Message Content */}
      <div className={cn("flex-1 space-y-2 min-w-0", isUser && "flex flex-col items-end")}>
        <div
          className={cn(
            "rounded-2xl px-4 py-3 max-w-[80%]",
            isUser
              ? "bg-neutral-800 text-white"
              : "bg-white border border-neutral-200 text-neutral-900",
          )}
        >
          <div className="whitespace-pre-wrap break-words text-sm">
            {message.content}
            {isStreaming && (
              <span className="inline-block h-4 w-1 animate-pulse bg-current ml-1" aria-hidden="true" />
            )}
          </div>
        </div>

        {/* Citations */}
        {!isUser && displaySources.length > 0 && (
          <div className="max-w-[80%] space-y-1.5">
            {displaySources.map((source, i) => (
              <SourceCard key={i} source={source} />
            ))}
          </div>
        )}

        {/* Confidence + Feedback */}
        {!isUser && (
          <div className="flex items-center gap-3">
            {message.confidence_level && (
              <ConfidenceIndicator level={message.confidence_level} />
            )}
            {!isStreaming && message.id !== "streaming" && (
              <FeedbackButtons
                messageId={message.id}
                existingFeedback={message.feedback}
              />
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function SourceCard({ source }: { source: SourceData }) {
  switch (source.type) {
    case "legal":
      return (
        <LegalSource
          actName={source.act_name as string}
          section={source.section as string}
          uri={source.uri as string}
          verificationStatus={source.verification_status as VerificationStatus}
        />
      );
    case "case_law":
      return (
        <CaseLawSource
          caseName={source.case_name as string}
          citation={source.citation as string}
          court={source.court as string}
          date={source.date as string}
        />
      );
    case "company_policy":
      return (
        <CompanyPolicySource
          documentName={source.document_name as string}
          section={source.section as string}
        />
      );
    case "parliamentary":
      return (
        <ParliamentarySource
          type={source.parliamentary_type as string}
          reference={source.reference as string}
          date={source.date as string}
          member={source.member as string | undefined}
        />
      );
    default:
      return null;
  }
}
