"use client";

/**
 * PersonaSelector — Dropdown to select an AI persona before sending a message.
 */

import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@/lib/auth/auth-context";
import { usePersonaStore } from "@/stores/persona-store";
import { Bot, ChevronDown, X } from "lucide-react";
import { cn } from "@/lib/utils/cn";
import { useState, useRef, useEffect } from "react";

export function PersonaSelector() {
  const { api } = useAuth();
  const { activePersonaId, activePersonaName, selectPersona, clearPersona } =
    usePersonaStore();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const { data } = useQuery({
    queryKey: ["personas"],
    queryFn: () => api.personas.list({ page: 1, page_size: 50 }),
  });

  const personas = data?.items ?? [];

  // Close on click outside
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(!open)}
        className={cn(
          "flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium transition-colors",
          activePersonaId
            ? "border-blue-300 bg-blue-50 text-blue-700"
            : "border-neutral-200 bg-white text-neutral-600 hover:bg-neutral-50",
        )}
        aria-expanded={open}
        aria-haspopup="listbox"
      >
        <Bot className="h-3.5 w-3.5" />
        {activePersonaName || "Default persona"}
        <ChevronDown className="h-3 w-3" />
      </button>

      {activePersonaId && (
        <button
          onClick={(e) => {
            e.stopPropagation();
            clearPersona();
          }}
          className="ml-1 rounded-full p-0.5 text-neutral-400 hover:text-neutral-600"
          aria-label="Clear persona"
        >
          <X className="h-3 w-3" />
        </button>
      )}

      {open && (
        <div
          className="absolute bottom-full left-0 z-10 mb-1 w-64 rounded-lg border border-neutral-200 bg-white py-1 shadow-lg"
          role="listbox"
          aria-label="Select persona"
        >
          <button
            onClick={() => {
              clearPersona();
              setOpen(false);
            }}
            className={cn(
              "flex w-full items-start gap-2 px-3 py-2 text-left text-sm hover:bg-neutral-50",
              !activePersonaId && "bg-neutral-50",
            )}
            role="option"
            aria-selected={!activePersonaId}
          >
            <Bot className="mt-0.5 h-4 w-4 text-neutral-400" />
            <div>
              <div className="font-medium text-neutral-900">Default</div>
              <div className="text-xs text-neutral-500">Standard AI assistant</div>
            </div>
          </button>

          {personas.map((persona) => (
            <button
              key={persona.id}
              onClick={() => {
                selectPersona(persona.id, persona.name);
                setOpen(false);
              }}
              className={cn(
                "flex w-full items-start gap-2 px-3 py-2 text-left text-sm hover:bg-neutral-50",
                activePersonaId === persona.id && "bg-blue-50",
              )}
              role="option"
              aria-selected={activePersonaId === persona.id}
            >
              <Bot className="mt-0.5 h-4 w-4 text-blue-500" />
              <div>
                <div className="font-medium text-neutral-900">{persona.name}</div>
                {persona.description && (
                  <div className="text-xs text-neutral-500 line-clamp-2">
                    {persona.description}
                  </div>
                )}
              </div>
            </button>
          ))}

          {personas.length === 0 && (
            <div className="px-3 py-2 text-xs text-neutral-500">No personas configured</div>
          )}
        </div>
      )}
    </div>
  );
}
