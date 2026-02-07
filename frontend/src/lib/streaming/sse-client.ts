/**
 * SSE Client — Server-Sent Events client for agent streaming
 */

import { tokenStorage } from "../auth/token-storage";

/**
 * SSE Event types (matching backend SSEEventType enum)
 */
export type SSEEventType =
  | "agent_start"
  | "agent_progress"
  | "agent_complete"
  | "content_delta"
  | "content_block_start"
  | "content_block_end"
  | "message_state"
  | "message_complete"
  | "verification_result"
  | "confidence_update"
  | "conversation_title_updating"
  | "conversation_title_updated"
  | "citation_inline"
  | "source_added"
  | "usage_metrics"
  | "error";

/**
 * Base SSE event shape
 */
export interface SSEEvent<T = unknown> {
  event: SSEEventType;
  data: T;
  timestamp: string;
  sequence?: number;
}

/**
 * Event data types
 */
export interface AgentStartEvent {
  agent_name: string;
  task_description?: string;
}

export interface AgentCompleteEvent {
  agent_name: string;
  duration_ms?: number;
}

export interface ContentDeltaEvent {
  text: string;
}

export interface VerificationResultEvent {
  citations_checked: number;
  citations_verified: number;
  issues: string[];
}

export interface ConfidenceUpdateEvent {
  level: "high" | "medium" | "low";
  reason?: string;
}

export interface MessageCompleteEvent {
  message_id: string;
}

export interface ConversationTitleUpdatedEvent {
  conversation_id: string;
  title: string;
}

export interface ErrorEvent {
  error: string;
  details?: string;
}

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
    onEvent: (event: SSEEvent) => void,
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
    this.eventSource.onmessage = (event) => {
      try {
        const parsedEvent: SSEEvent = JSON.parse(event.data);
        onEvent(parsedEvent);
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
