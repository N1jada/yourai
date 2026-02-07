import { describe, it, expect, beforeEach } from "vitest";
import { useSidebarStore } from "@/stores/sidebar-store";

describe("useSidebarStore", () => {
  beforeEach(() => {
    // Reset store state
    useSidebarStore.setState({ isOpen: true });
  });

  it("starts with sidebar open", () => {
    expect(useSidebarStore.getState().isOpen).toBe(true);
  });

  it("toggles sidebar", () => {
    useSidebarStore.getState().toggle();
    expect(useSidebarStore.getState().isOpen).toBe(false);
    useSidebarStore.getState().toggle();
    expect(useSidebarStore.getState().isOpen).toBe(true);
  });

  it("opens sidebar", () => {
    useSidebarStore.setState({ isOpen: false });
    useSidebarStore.getState().open();
    expect(useSidebarStore.getState().isOpen).toBe(true);
  });

  it("closes sidebar", () => {
    useSidebarStore.getState().close();
    expect(useSidebarStore.getState().isOpen).toBe(false);
  });
});
