/**
 * AgentProgress — Shows sub-agent activity during streaming.
 */

import { Bot, Check, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils/cn";

interface AgentStatus {
  name: string;
  status: "running" | "complete";
  taskDescription?: string;
  statusText?: string;
  durationMs?: number;
}

interface AgentProgressProps {
  agents: AgentStatus[];
  className?: string;
}

export function AgentProgress({ agents, className }: AgentProgressProps) {
  if (agents.length === 0) return null;

  return (
    <div
      className={cn("flex flex-wrap gap-2", className)}
      role="status"
      aria-label="Agent activity"
    >
      {agents.map((agent) => (
        <div
          key={agent.name}
          className={cn(
            "inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium",
            agent.status === "running"
              ? "border-blue-200 bg-blue-50 text-blue-700"
              : "border-green-200 bg-green-50 text-green-700",
          )}
        >
          {agent.status === "running" ? (
            <Loader2 className="h-3 w-3 animate-spin" aria-hidden="true" />
          ) : (
            <Check className="h-3 w-3" aria-hidden="true" />
          )}
          <Bot className="h-3 w-3" aria-hidden="true" />
          <span>{agent.statusText || agent.taskDescription || agent.name}</span>
          {agent.status === "complete" && agent.durationMs != null && (
            <span className="text-green-500">
              ({(agent.durationMs / 1000).toFixed(1)}s)
            </span>
          )}
        </div>
      ))}
    </div>
  );
}
