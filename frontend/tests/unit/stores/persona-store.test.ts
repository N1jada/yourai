import { describe, it, expect, beforeEach } from "vitest";
import { usePersonaStore } from "@/stores/persona-store";

describe("usePersonaStore", () => {
  beforeEach(() => {
    usePersonaStore.getState().clearPersona();
  });

  it("starts with no active persona", () => {
    const state = usePersonaStore.getState();
    expect(state.activePersonaId).toBeNull();
    expect(state.activePersonaName).toBeNull();
  });

  it("selects a persona", () => {
    usePersonaStore.getState().selectPersona("p-1", "Legal Expert");
    const state = usePersonaStore.getState();
    expect(state.activePersonaId).toBe("p-1");
    expect(state.activePersonaName).toBe("Legal Expert");
  });

  it("clears the active persona", () => {
    usePersonaStore.getState().selectPersona("p-1", "Legal Expert");
    usePersonaStore.getState().clearPersona();
    const state = usePersonaStore.getState();
    expect(state.activePersonaId).toBeNull();
    expect(state.activePersonaName).toBeNull();
  });

  it("replaces the previous persona when selecting a new one", () => {
    usePersonaStore.getState().selectPersona("p-1", "Legal Expert");
    usePersonaStore.getState().selectPersona("p-2", "Policy Advisor");
    const state = usePersonaStore.getState();
    expect(state.activePersonaId).toBe("p-2");
    expect(state.activePersonaName).toBe("Policy Advisor");
  });
});
