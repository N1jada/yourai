/**
 * Streaming Store — Tracks streaming state per conversation.
 */

import { create } from "zustand";
import type { ConfidenceLevel } from "@/lib/types/enums";

interface AgentStatus {
  name: string;
  status: "running" | "complete";
  taskDescription?: string;
  statusText?: string;
  durationMs?: number;
}

interface StreamingState {
  /** Conversation ID currently streaming, or null. */
  activeConversationId: string | null;
  /** Accumulated streaming text for the active conversation. */
  streamingText: string;
  /** Active sub-agents and their status. */
  agents: AgentStatus[];
  /** Current confidence level from the stream. */
  confidence: { level: ConfidenceLevel; reason: string } | null;
  /** Collected source citations during streaming. */
  sources: Record<string, unknown>[];
  /** Whether verification result has been received. */
  verificationResult: {
    citationsChecked: number;
    citationsVerified: number;
    issues: string[];
  } | null;

  // Actions
  startStreaming: (conversationId: string) => void;
  appendText: (text: string) => void;
  addAgent: (name: string, taskDescription: string) => void;
  updateAgent: (name: string, statusText: string) => void;
  completeAgent: (name: string, durationMs: number) => void;
  setConfidence: (level: ConfidenceLevel, reason: string) => void;
  addSource: (source: Record<string, unknown>) => void;
  setVerificationResult: (result: {
    citationsChecked: number;
    citationsVerified: number;
    issues: string[];
  }) => void;
  reset: () => void;
}

const initialState = {
  activeConversationId: null,
  streamingText: "",
  agents: [] as AgentStatus[],
  confidence: null,
  sources: [] as Record<string, unknown>[],
  verificationResult: null,
};

export const useStreamingStore = create<StreamingState>((set) => ({
  ...initialState,

  startStreaming: (conversationId) =>
    set({ ...initialState, activeConversationId: conversationId }),

  appendText: (text) =>
    set((s) => ({ streamingText: s.streamingText + text })),

  addAgent: (name, taskDescription) =>
    set((s) => ({
      agents: [
        ...s.agents.filter((a) => a.name !== name),
        { name, status: "running", taskDescription },
      ],
    })),

  updateAgent: (name, statusText) =>
    set((s) => ({
      agents: s.agents.map((a) =>
        a.name === name ? { ...a, statusText } : a,
      ),
    })),

  completeAgent: (name, durationMs) =>
    set((s) => ({
      agents: s.agents.map((a) =>
        a.name === name ? { ...a, status: "complete", durationMs } : a,
      ),
    })),

  setConfidence: (level, reason) => set({ confidence: { level, reason } }),

  addSource: (source) =>
    set((s) => ({ sources: [...s.sources, source] })),

  setVerificationResult: (result) => set({ verificationResult: result }),

  reset: () => set(initialState),
}));
