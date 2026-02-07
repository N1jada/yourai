import { describe, it, expect, beforeEach } from "vitest";
import { useStreamingStore } from "@/stores/streaming-store";

describe("useStreamingStore", () => {
  beforeEach(() => {
    useStreamingStore.getState().reset();
  });

  it("starts with no active conversation", () => {
    const state = useStreamingStore.getState();
    expect(state.activeConversationId).toBeNull();
    expect(state.streamingText).toBe("");
    expect(state.agents).toHaveLength(0);
  });

  it("starts streaming for a conversation", () => {
    useStreamingStore.getState().startStreaming("conv-1");
    expect(useStreamingStore.getState().activeConversationId).toBe("conv-1");
  });

  it("appends text incrementally", () => {
    useStreamingStore.getState().startStreaming("conv-1");
    useStreamingStore.getState().appendText("Hello ");
    useStreamingStore.getState().appendText("world");
    expect(useStreamingStore.getState().streamingText).toBe("Hello world");
  });

  it("manages agent lifecycle", () => {
    const store = useStreamingStore.getState();
    store.startStreaming("conv-1");
    store.addAgent("legal-researcher", "Searching legislation");

    let agents = useStreamingStore.getState().agents;
    expect(agents).toHaveLength(1);
    expect(agents[0].name).toBe("legal-researcher");
    expect(agents[0].status).toBe("running");

    useStreamingStore.getState().updateAgent("legal-researcher", "Found 3 results");
    agents = useStreamingStore.getState().agents;
    expect(agents[0].statusText).toBe("Found 3 results");

    useStreamingStore.getState().completeAgent("legal-researcher", 1500);
    agents = useStreamingStore.getState().agents;
    expect(agents[0].status).toBe("complete");
    expect(agents[0].durationMs).toBe(1500);
  });

  it("sets confidence level", () => {
    useStreamingStore.getState().setConfidence("high", "Multiple sources");
    const state = useStreamingStore.getState();
    expect(state.confidence?.level).toBe("high");
    expect(state.confidence?.reason).toBe("Multiple sources");
  });

  it("accumulates sources", () => {
    useStreamingStore.getState().addSource({ type: "legal", title: "Act 1" });
    useStreamingStore.getState().addSource({ type: "case_law", title: "Case 2" });
    expect(useStreamingStore.getState().sources).toHaveLength(2);
  });

  it("sets verification result", () => {
    useStreamingStore.getState().setVerificationResult({
      citationsChecked: 5,
      citationsVerified: 4,
      issues: ["One source outdated"],
    });
    const result = useStreamingStore.getState().verificationResult;
    expect(result?.citationsChecked).toBe(5);
    expect(result?.citationsVerified).toBe(4);
    expect(result?.issues).toHaveLength(1);
  });

  it("resets all state", () => {
    useStreamingStore.getState().startStreaming("conv-1");
    useStreamingStore.getState().appendText("Some text");
    useStreamingStore.getState().addAgent("agent-1", "task");
    useStreamingStore.getState().setConfidence("high", "reason");

    useStreamingStore.getState().reset();

    const state = useStreamingStore.getState();
    expect(state.activeConversationId).toBeNull();
    expect(state.streamingText).toBe("");
    expect(state.agents).toHaveLength(0);
    expect(state.confidence).toBeNull();
    expect(state.sources).toHaveLength(0);
  });

  it("replaces agent if added with same name", () => {
    useStreamingStore.getState().addAgent("agent-1", "task 1");
    useStreamingStore.getState().addAgent("agent-1", "task 2");
    expect(useStreamingStore.getState().agents).toHaveLength(1);
    expect(useStreamingStore.getState().agents[0].taskDescription).toBe("task 2");
  });
});
