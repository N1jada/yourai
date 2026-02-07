"use client";

/**
 * FeedbackButtons — Thumbs up/down on assistant messages.
 */

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { useAuth } from "@/lib/auth/auth-context";
import { ThumbsUp, ThumbsDown } from "lucide-react";
import { cn } from "@/lib/utils/cn";
import type { FeedbackRating } from "@/lib/types/enums";
import type { FeedbackResponse } from "@/lib/types/conversations";

interface FeedbackButtonsProps {
  messageId: string;
  existingFeedback: FeedbackResponse | null;
}

export function FeedbackButtons({ messageId, existingFeedback }: FeedbackButtonsProps) {
  const { api } = useAuth();
  const [currentRating, setCurrentRating] = useState<FeedbackRating | null>(
    existingFeedback?.rating ?? null,
  );
  const [showComment, setShowComment] = useState(false);
  const [comment, setComment] = useState(existingFeedback?.comment ?? "");

  const submitMutation = useMutation({
    mutationFn: (rating: FeedbackRating) =>
      api.feedback.submit(messageId, {
        rating,
        comment: comment || undefined,
      }),
    onSuccess: (_, rating) => {
      setCurrentRating(rating);
      setShowComment(false);
    },
  });

  const handleRate = (rating: FeedbackRating) => {
    if (currentRating === rating) return;
    if (rating === "down") {
      setShowComment(true);
    } else {
      submitMutation.mutate(rating);
    }
  };

  return (
    <div className="flex items-center gap-1">
      <button
        onClick={() => handleRate("up")}
        disabled={submitMutation.isPending}
        className={cn(
          "rounded-md p-1 transition-colors",
          currentRating === "up"
            ? "text-green-600 bg-green-50"
            : "text-neutral-400 hover:text-green-600 hover:bg-green-50",
        )}
        aria-label="Helpful"
        aria-pressed={currentRating === "up"}
      >
        <ThumbsUp className="h-3.5 w-3.5" />
      </button>
      <button
        onClick={() => handleRate("down")}
        disabled={submitMutation.isPending}
        className={cn(
          "rounded-md p-1 transition-colors",
          currentRating === "down"
            ? "text-red-600 bg-red-50"
            : "text-neutral-400 hover:text-red-600 hover:bg-red-50",
        )}
        aria-label="Not helpful"
        aria-pressed={currentRating === "down"}
      >
        <ThumbsDown className="h-3.5 w-3.5" />
      </button>

      {showComment && (
        <div className="ml-2 flex items-center gap-1">
          <input
            type="text"
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder="What could be better?"
            className="rounded border border-neutral-200 px-2 py-1 text-xs"
            onKeyDown={(e) => {
              if (e.key === "Enter") submitMutation.mutate("down");
            }}
          />
          <button
            onClick={() => submitMutation.mutate("down")}
            className="rounded bg-neutral-800 px-2 py-1 text-xs text-white hover:bg-neutral-700"
          >
            Send
          </button>
          <button
            onClick={() => setShowComment(false)}
            className="px-1 text-xs text-neutral-500 hover:text-neutral-700"
          >
            Cancel
          </button>
        </div>
      )}
    </div>
  );
}
