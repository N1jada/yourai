"use client";

/**
 * Activity Log Page — Filterable audit trail with CSV export.
 */

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@/lib/auth/auth-context";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { SkeletonRow } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils/cn";
import { Download, Filter, Search, Activity } from "lucide-react";
import type { ActivityLogFilters, ActivityLogResponse } from "@/lib/api/endpoints";

const tagColors: Record<string, string> = {
  user: "bg-blue-100 text-blue-700",
  system: "bg-neutral-100 text-neutral-600",
  security: "bg-red-100 text-red-700",
  ai: "bg-purple-100 text-purple-700",
};

export default function ActivityLogPage() {
  const { api } = useAuth();
  const [showFilters, setShowFilters] = useState(false);
  const [filters, setFilters] = useState<ActivityLogFilters>({
    page: 1,
    page_size: 50,
  });

  const { data, isLoading } = useQuery({
    queryKey: ["activity-logs", filters],
    queryFn: () => api.activityLogs.list(filters),
  });

  const logs = data?.items ?? [];

  const handleExport = async () => {
    try {
      const csv = await api.activityLogs.exportCsv({
        tag: filters.tag,
        user_id: filters.user_id,
        date_from: filters.date_from,
        date_to: filters.date_to,
      });
      const blob = new Blob([csv], { type: "text/csv" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `activity-log-${new Date().toISOString().slice(0, 10)}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error("Export failed:", error);
    }
  };

  return (
    <div className="flex h-full flex-col">
      {/* Toolbar */}
      <div className="flex items-center gap-3 border-b border-neutral-100 bg-white px-6 py-3">
        <Button
          variant="outline"
          size="sm"
          onClick={() => setShowFilters(!showFilters)}
        >
          <Filter className="mr-2 h-4 w-4" />
          Filters
        </Button>
        <Button variant="outline" size="sm" onClick={handleExport}>
          <Download className="mr-2 h-4 w-4" />
          Export CSV
        </Button>
      </div>

      {/* Filter panel */}
      {showFilters && (
        <div className="border-b border-neutral-100 bg-neutral-50 px-6 py-4">
          <div className="flex flex-wrap items-end gap-3">
            <div>
              <label className="text-xs text-neutral-500">Tag</label>
              <select
                value={filters.tag ?? ""}
                onChange={(e) =>
                  setFilters((f) => ({
                    ...f,
                    tag: e.target.value || undefined,
                    page: 1,
                  }))
                }
                className="flex h-10 w-full rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
              >
                <option value="">All</option>
                <option value="user">User</option>
                <option value="system">System</option>
                <option value="security">Security</option>
                <option value="ai">AI</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-neutral-500">From</label>
              <Input
                type="date"
                value={filters.date_from ?? ""}
                onChange={(e) =>
                  setFilters((f) => ({
                    ...f,
                    date_from: e.target.value || undefined,
                    page: 1,
                  }))
                }
              />
            </div>
            <div>
              <label className="text-xs text-neutral-500">To</label>
              <Input
                type="date"
                value={filters.date_to ?? ""}
                onChange={(e) =>
                  setFilters((f) => ({
                    ...f,
                    date_to: e.target.value || undefined,
                    page: 1,
                  }))
                }
              />
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={() =>
                setFilters({ page: 1, page_size: 50 })
              }
            >
              Clear
            </Button>
          </div>
        </div>
      )}

      {/* Table */}
      <div className="flex-1 overflow-y-auto">
        {isLoading ? (
          <div className="space-y-1">
            <SkeletonRow />
            <SkeletonRow />
            <SkeletonRow />
            <SkeletonRow />
          </div>
        ) : logs.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-neutral-500">
            <Activity className="h-12 w-12" />
            <p className="mt-4">No activity logged</p>
          </div>
        ) : (
          <table className="w-full">
            <thead className="border-b border-neutral-200 bg-neutral-50 text-left text-xs font-medium uppercase text-neutral-500">
              <tr>
                <th className="px-6 py-3">Time</th>
                <th className="px-6 py-3">User</th>
                <th className="px-6 py-3">Action</th>
                <th className="px-6 py-3">Detail</th>
                <th className="px-6 py-3">Tags</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-100">
              {logs.map((log) => (
                <LogRow key={log.id} log={log} />
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Pagination */}
      {data && data.has_next && (
        <div className="border-t border-neutral-200 bg-white px-6 py-3 text-center">
          <Button
            variant="ghost"
            size="sm"
            onClick={() =>
              setFilters((f) => ({ ...f, page: (f.page ?? 1) + 1 }))
            }
          >
            Load more
          </Button>
        </div>
      )}
    </div>
  );
}

function LogRow({ log }: { log: ActivityLogResponse }) {
  return (
    <tr className="hover:bg-neutral-50">
      <td className="whitespace-nowrap px-6 py-3 text-sm text-neutral-500">
        {log.created_at
          ? new Date(log.created_at).toLocaleString()
          : "\u2014"}
      </td>
      <td className="px-6 py-3 text-sm font-medium text-neutral-900">
        {log.user_name ?? "\u2014"}
      </td>
      <td className="px-6 py-3 text-sm text-neutral-700">{log.action}</td>
      <td className="max-w-xs truncate px-6 py-3 text-sm text-neutral-600">
        {log.detail ?? "\u2014"}
      </td>
      <td className="px-6 py-3">
        <div className="flex gap-1">
          {log.tags.map((tag) => (
            <span
              key={tag}
              className={cn(
                "rounded-full px-2 py-0.5 text-xs font-medium capitalize",
                tagColors[tag] ?? "bg-neutral-100 text-neutral-600",
              )}
            >
              {tag}
            </span>
          ))}
        </div>
      </td>
    </tr>
  );
}
