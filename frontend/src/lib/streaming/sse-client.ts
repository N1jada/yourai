/**
 * SSE Client — Server-Sent Events client for agent streaming
 */

import { tokenStorage } from "../auth/token-storage";
import type { AnySSEEvent, SSEEventType } from "@/lib/types/stream";

/**
 * Wrapper adding timestamp and optional sequence number to parsed events.
 */
export interface SSEEventEnvelope<T = AnySSEEvent> {
  event: SSEEventType;
  data: T;
  timestamp: string;
  sequence?: number;
}

// Re-export stream types for consumer convenience
export type { SSEEventType, AnySSEEvent } from "@/lib/types/stream";
export type {
  AgentStartEvent,
  AgentCompleteEvent,
  ContentDeltaEvent,
  VerificationResultEvent,
  ConfidenceUpdateEvent,
  MessageCompleteEvent,
  ConversationTitleUpdatedEvent,
  ErrorEvent,
  StreamEvent,
  UserPushEvent,
} from "@/lib/types/stream";

/** @deprecated Use SSEEventEnvelope instead */
export type SSEEvent<T = unknown> = SSEEventEnvelope<T>;

/**
 * SSE Client for conversation streams
 */
export class SSEClient {
  private eventSource: EventSource | null = null;
  private baseUrl: string;

  constructor(baseUrl?: string) {
    this.baseUrl = baseUrl || process.env.NEXT_PUBLIC_API_BASE_URL || "";
  }

  /**
   * Connect to conversation SSE stream
   */
  connect(
    conversationId: string,
    onEvent: (event: SSEEventEnvelope) => void,
    onError?: (error: Error) => void,
  ): () => void {
    const token = tokenStorage.getToken();
    if (!token) {
      throw new Error("No auth token available");
    }

    // EventSource doesn't support custom headers, so pass token as query param
    const url = `${this.baseUrl}/api/v1/conversations/${conversationId}/stream?token=${encodeURIComponent(token)}`;

    this.eventSource = new EventSource(url);

    // Handle all event types
    // Backend sends raw Pydantic events (e.g. {"event_type":"content_delta","text":"..."})
    // We wrap them in the SSEEventEnvelope format the frontend expects.
    this.eventSource.onmessage = (event) => {
      try {
        const rawEvent = JSON.parse(event.data);
        const envelope: SSEEventEnvelope = {
          event: rawEvent.event_type,
          data: rawEvent,
          timestamp: new Date().toISOString(),
        };
        onEvent(envelope);
      } catch (error) {
        console.error("Failed to parse SSE event:", error);
      }
    };

    // Handle errors
    this.eventSource.onerror = (event) => {
      console.error("SSE connection error:", event);
      onError?.(new Error("SSE connection failed"));
      this.disconnect();
    };

    // Return cleanup function
    return () => this.disconnect();
  }

  /**
   * Disconnect from stream
   */
  disconnect(): void {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
  }
}
