/**
 * Persona Store — Tracks the active AI persona selection.
 */

import { create } from "zustand";
import { persist } from "zustand/middleware";

interface PersonaState {
  /** Currently selected persona ID, or null for default. */
  activePersonaId: string | null;
  /** Display name of the active persona. */
  activePersonaName: string | null;

  // Actions
  selectPersona: (id: string, name: string) => void;
  clearPersona: () => void;
}

export const usePersonaStore = create<PersonaState>()(
  persist(
    (set) => ({
      activePersonaId: null,
      activePersonaName: null,

      selectPersona: (id, name) =>
        set({ activePersonaId: id, activePersonaName: name }),

      clearPersona: () =>
        set({ activePersonaId: null, activePersonaName: null }),
    }),
    { name: "yourai-persona" },
  ),
);
