"use client";

/**
 * Legislation Admin Page — Lex health, browse legislation, and connection settings.
 */

import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/lib/auth/auth-context";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { SkeletonCard } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils/cn";
import {
  BookOpen,
  Search,
  RefreshCw,
  Wifi,
  WifiOff,
  AlertTriangle,
  Settings,
  ChevronDown,
  ChevronRight,
} from "lucide-react";
import type {
  LegislationSearchResultItem,
  LegislationDetailResponse,
} from "@/lib/types/legislation";

type Tab = "overview" | "browse" | "settings";

const statusConfig: Record<
  string,
  { label: string; color: string; icon: typeof Wifi }
> = {
  connected: {
    label: "Connected",
    color: "bg-green-100 text-green-700",
    icon: Wifi,
  },
  fallback: {
    label: "Fallback",
    color: "bg-amber-100 text-amber-700",
    icon: AlertTriangle,
  },
  error: {
    label: "Error",
    color: "bg-red-100 text-red-700",
    icon: WifiOff,
  },
};

export default function LegislationAdminPage() {
  const [activeTab, setActiveTab] = useState<Tab>("overview");

  const tabs: { key: Tab; label: string }[] = [
    { key: "overview", label: "Overview" },
    { key: "browse", label: "Browse" },
    { key: "settings", label: "Settings" },
  ];

  return (
    <div className="flex h-full flex-col overflow-y-auto">
      {/* Sub-tabs */}
      <div className="border-b border-neutral-100 bg-white px-6">
        <div className="flex gap-4">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={cn(
                "border-b-2 pb-2.5 pt-3 text-sm font-medium transition-colors",
                activeTab === tab.key
                  ? "border-neutral-900 text-neutral-900"
                  : "border-transparent text-neutral-500 hover:text-neutral-700",
              )}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 p-6">
        {activeTab === "overview" && <OverviewSection />}
        {activeTab === "browse" && <BrowseSection />}
        {activeTab === "settings" && <SettingsSection />}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Overview
// ---------------------------------------------------------------------------

function OverviewSection() {
  const { api } = useAuth();

  const { data, isLoading } = useQuery({
    queryKey: ["admin-legislation-overview"],
    queryFn: () => api.legislation.getOverview(),
  });

  if (isLoading) {
    return (
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <SkeletonCard />
        <SkeletonCard />
        <SkeletonCard />
        <SkeletonCard />
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex flex-col items-center py-12 text-neutral-500">
        <WifiOff className="h-12 w-12" />
        <p className="mt-4">Could not load Lex status</p>
      </div>
    );
  }

  const cfg = statusConfig[data.status] ?? statusConfig.error;
  const StatusIcon = cfg.icon;
  const stats = data.stats;

  return (
    <div className="space-y-6">
      {/* Status card */}
      <div className="rounded-lg border border-neutral-200 bg-white p-5">
        <div className="flex items-center gap-3">
          <StatusIcon className="h-5 w-5 text-neutral-600" />
          <h3 className="font-semibold text-neutral-900">
            Lex Connection Status
          </h3>
          <span
            className={cn(
              "rounded-full px-2.5 py-0.5 text-xs font-medium",
              cfg.color,
            )}
          >
            {cfg.label}
          </span>
        </div>
        <div className="mt-3 grid gap-2 text-sm text-neutral-600 sm:grid-cols-2">
          <div>
            <span className="font-medium text-neutral-500">Active URL: </span>
            <code className="text-xs">{data.active_url}</code>
          </div>
          {data.is_using_fallback && (
            <div>
              <span className="text-amber-600">
                Using fallback — primary is unreachable
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Stats grid */}
      {stats && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Object.entries(stats).map(([key, value]) => (
            <div
              key={key}
              className="rounded-lg border border-neutral-200 bg-white p-4"
            >
              <p className="text-xs font-medium uppercase text-neutral-500">
                {key.replace(/_/g, " ")}
              </p>
              <p className="mt-1 text-2xl font-bold text-neutral-900">
                {typeof value === "number" ? value.toLocaleString() : String(value ?? "\u2014")}
              </p>
            </div>
          ))}
        </div>
      )}

      {!stats && (
        <div className="rounded-lg border border-neutral-200 bg-neutral-50 p-4 text-sm text-neutral-500">
          Statistics unavailable — Lex API may be unreachable.
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Browse
// ---------------------------------------------------------------------------

function BrowseSection() {
  const { api } = useAuth();
  const [query, setQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [yearFrom, setYearFrom] = useState("");
  const [yearTo, setYearTo] = useState("");
  const [offset, setOffset] = useState(0);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  // Debounce search query
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(query);
      setOffset(0);
    }, 400);
    return () => clearTimeout(timer);
  }, [query]);

  const { data, isLoading } = useQuery({
    queryKey: [
      "admin-legislation-search",
      debouncedQuery,
      yearFrom,
      yearTo,
      offset,
    ],
    queryFn: () =>
      api.legislation.search({
        query: debouncedQuery,
        year_from: yearFrom ? parseInt(yearFrom, 10) : undefined,
        year_to: yearTo ? parseInt(yearTo, 10) : undefined,
        offset,
        limit: 20,
      }),
    enabled: debouncedQuery.length > 0,
  });

  const results = data?.results ?? [];

  return (
    <div className="space-y-4">
      {/* Search toolbar */}
      <div className="flex flex-wrap items-end gap-3">
        <div className="flex-1">
          <label className="text-xs text-neutral-500">Search</label>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-400" />
            <Input
              className="pl-10"
              placeholder="Search legislation by title or keyword..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </div>
        </div>
        <div className="w-28">
          <label className="text-xs text-neutral-500">Year from</label>
          <Input
            type="number"
            min={1800}
            max={2099}
            placeholder="1900"
            value={yearFrom}
            onChange={(e) => {
              setYearFrom(e.target.value);
              setOffset(0);
            }}
          />
        </div>
        <div className="w-28">
          <label className="text-xs text-neutral-500">Year to</label>
          <Input
            type="number"
            min={1800}
            max={2099}
            placeholder="2026"
            value={yearTo}
            onChange={(e) => {
              setYearTo(e.target.value);
              setOffset(0);
            }}
          />
        </div>
      </div>

      {/* Results */}
      {!debouncedQuery && (
        <div className="flex flex-col items-center py-12 text-neutral-500">
          <BookOpen className="h-12 w-12" />
          <p className="mt-4">Enter a search term to browse legislation</p>
        </div>
      )}

      {debouncedQuery && isLoading && (
        <div className="space-y-2">
          <SkeletonCard />
          <SkeletonCard />
        </div>
      )}

      {debouncedQuery && !isLoading && results.length === 0 && (
        <div className="flex flex-col items-center py-12 text-neutral-500">
          <Search className="h-12 w-12" />
          <p className="mt-4">No legislation found</p>
        </div>
      )}

      {results.length > 0 && (
        <>
          <p className="text-sm text-neutral-500">
            {data?.total ?? 0} result{(data?.total ?? 0) !== 1 ? "s" : ""} found
          </p>

          <div className="overflow-hidden rounded-lg border border-neutral-200 bg-white">
            <table className="w-full">
              <thead className="border-b border-neutral-200 bg-neutral-50 text-left text-xs font-medium uppercase text-neutral-500">
                <tr>
                  <th className="px-4 py-3" />
                  <th className="px-4 py-3">Title</th>
                  <th className="px-4 py-3">Type</th>
                  <th className="px-4 py-3">Year</th>
                  <th className="px-4 py-3">Number</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Provisions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-100">
                {results.map((item, idx) => {
                  const itemId = `${String(item.type)}-${String(item.year)}-${String(item.number)}-${String(idx)}`;
                  const isExpanded = expandedId === itemId;

                  return (
                    <ResultRow
                      key={itemId}
                      item={item}
                      isExpanded={isExpanded}
                      onToggle={() =>
                        setExpandedId(isExpanded ? null : itemId)
                      }
                    />
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {data && offset + 20 < data.total && (
            <div className="text-center">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setOffset((o) => o + 20)}
              >
                Load more
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function ResultRow({
  item,
  isExpanded,
  onToggle,
}: {
  item: LegislationSearchResultItem;
  isExpanded: boolean;
  onToggle: () => void;
}) {
  const { api } = useAuth();

  const { data: detail, isLoading: detailLoading } = useQuery({
    queryKey: ["admin-legislation-detail", item.type, item.year, item.number],
    queryFn: () =>
      api.legislation.getDetail(
        String(item.type),
        Number(item.year),
        Number(item.number),
      ),
    enabled: isExpanded && !!item.type && !!item.year && item.number != null,
  });

  return (
    <>
      <tr
        className="cursor-pointer hover:bg-neutral-50"
        onClick={onToggle}
      >
        <td className="px-4 py-3">
          {isExpanded ? (
            <ChevronDown className="h-4 w-4 text-neutral-400" />
          ) : (
            <ChevronRight className="h-4 w-4 text-neutral-400" />
          )}
        </td>
        <td className="max-w-sm px-4 py-3 text-sm font-medium text-neutral-900">
          {item.title ?? "\u2014"}
        </td>
        <td className="px-4 py-3 text-sm text-neutral-600">
          {item.type ? String(item.type).toUpperCase() : "\u2014"}
        </td>
        <td className="px-4 py-3 text-sm text-neutral-600">
          {item.year ?? "\u2014"}
        </td>
        <td className="px-4 py-3 text-sm text-neutral-600">
          {item.number ?? "\u2014"}
        </td>
        <td className="px-4 py-3 text-sm">
          <span className="rounded-full bg-neutral-100 px-2 py-0.5 text-xs font-medium capitalize text-neutral-600">
            {item.status ?? "\u2014"}
          </span>
        </td>
        <td className="px-4 py-3 text-sm text-neutral-600">
          {item.number_of_provisions ?? "\u2014"}
        </td>
      </tr>

      {isExpanded && (
        <tr>
          <td colSpan={7} className="bg-neutral-50 px-6 py-4">
            {detailLoading ? (
              <p className="text-sm text-neutral-500">Loading details...</p>
            ) : detail ? (
              <DetailPanel detail={detail} />
            ) : (
              <p className="text-sm text-neutral-500">
                Could not load details.
              </p>
            )}
          </td>
        </tr>
      )}
    </>
  );
}

function DetailPanel({ detail }: { detail: LegislationDetailResponse }) {
  return (
    <div className="space-y-4">
      {/* Description */}
      {detail.legislation.description != null && (
        <div>
          <h4 className="text-xs font-medium uppercase text-neutral-500">
            Description
          </h4>
          <p className="mt-1 text-sm text-neutral-700">
            {String(detail.legislation.description)}
          </p>
        </div>
      )}

      {/* Sections */}
      <div>
        <h4 className="text-xs font-medium uppercase text-neutral-500">
          Sections ({detail.sections.length})
        </h4>
        {detail.sections.length > 0 ? (
          <ul className="mt-1 max-h-48 space-y-1 overflow-y-auto">
            {detail.sections.slice(0, 50).map((sec, i) => (
              <li key={i} className="text-sm text-neutral-600">
                <span className="font-medium">
                  {sec.number != null ? `S.${String(sec.number)}` : ""}
                </span>{" "}
                {sec.title ? String(sec.title) : ""}
              </li>
            ))}
            {detail.sections.length > 50 && (
              <li className="text-xs text-neutral-400">
                ...and {detail.sections.length - 50} more
              </li>
            )}
          </ul>
        ) : (
          <p className="mt-1 text-sm text-neutral-400">No sections</p>
        )}
      </div>

      {/* Amendments */}
      <div>
        <h4 className="text-xs font-medium uppercase text-neutral-500">
          Amendments ({detail.amendments.length})
        </h4>
        {detail.amendments.length > 0 ? (
          <ul className="mt-1 max-h-48 space-y-1 overflow-y-auto">
            {detail.amendments.slice(0, 20).map((amd, i) => (
              <li key={i} className="text-sm text-neutral-600">
                {amd.affecting_legislation
                  ? String(amd.affecting_legislation)
                  : String(amd.affecting_url ?? "")}
                {amd.type_of_effect
                  ? ` \u2014 ${String(amd.type_of_effect)}`
                  : ""}
              </li>
            ))}
            {detail.amendments.length > 20 && (
              <li className="text-xs text-neutral-400">
                ...and {detail.amendments.length - 20} more
              </li>
            )}
          </ul>
        ) : (
          <p className="mt-1 text-sm text-neutral-400">No amendments</p>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Settings
// ---------------------------------------------------------------------------

function SettingsSection() {
  const { api } = useAuth();
  const queryClient = useQueryClient();

  const { data: overview } = useQuery({
    queryKey: ["admin-legislation-overview"],
    queryFn: () => api.legislation.getOverview(),
  });

  const healthMutation = useMutation({
    mutationFn: () => api.legislation.checkHealth(),
    onSuccess: () =>
      queryClient.invalidateQueries({
        queryKey: ["admin-legislation-overview"],
      }),
  });

  const forcePrimaryMutation = useMutation({
    mutationFn: () => api.legislation.forcePrimary(),
    onSuccess: () =>
      queryClient.invalidateQueries({
        queryKey: ["admin-legislation-overview"],
      }),
  });

  return (
    <div className="space-y-6">
      {/* Connection info */}
      <div className="rounded-lg border border-neutral-200 bg-white p-5">
        <div className="flex items-center gap-2">
          <Settings className="h-5 w-5 text-neutral-500" />
          <h3 className="font-semibold text-neutral-900">
            Connection Configuration
          </h3>
        </div>
        <div className="mt-4 space-y-3 text-sm">
          <div className="flex justify-between">
            <span className="text-neutral-500">Primary URL</span>
            <code className="text-xs text-neutral-700">
              {overview?.primary_url ?? "\u2014"}
            </code>
          </div>
          <div className="flex justify-between">
            <span className="text-neutral-500">Fallback URL</span>
            <code className="text-xs text-neutral-700">
              {overview?.fallback_url ?? "\u2014"}
            </code>
          </div>
          <div className="flex justify-between">
            <span className="text-neutral-500">Active URL</span>
            <code className="text-xs font-medium text-neutral-900">
              {overview?.active_url ?? "\u2014"}
            </code>
          </div>
          <div className="flex justify-between">
            <span className="text-neutral-500">Using Fallback</span>
            <span
              className={cn(
                "text-xs font-medium",
                overview?.is_using_fallback
                  ? "text-amber-600"
                  : "text-green-600",
              )}
            >
              {overview?.is_using_fallback ? "Yes" : "No"}
            </span>
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="rounded-lg border border-neutral-200 bg-white p-5">
        <h3 className="font-semibold text-neutral-900">Actions</h3>
        <div className="mt-4 flex gap-3">
          <Button
            variant="outline"
            onClick={() => healthMutation.mutate()}
            disabled={healthMutation.isPending}
          >
            <RefreshCw
              className={cn(
                "mr-2 h-4 w-4",
                healthMutation.isPending && "animate-spin",
              )}
            />
            Check Health
          </Button>
          <Button
            variant="outline"
            onClick={() => forcePrimaryMutation.mutate()}
            disabled={forcePrimaryMutation.isPending}
          >
            Force Primary
          </Button>
        </div>

        {healthMutation.data && (
          <div className="mt-3 rounded border border-neutral-100 bg-neutral-50 p-3 text-sm">
            <p>
              Primary healthy:{" "}
              <span
                className={cn(
                  "font-medium",
                  healthMutation.data.primary_healthy
                    ? "text-green-600"
                    : "text-red-600",
                )}
              >
                {healthMutation.data.primary_healthy ? "Yes" : "No"}
              </span>
            </p>
            <p className="text-neutral-500">
              Status: {healthMutation.data.status} | Active:{" "}
              {healthMutation.data.active_url}
            </p>
          </div>
        )}

        {forcePrimaryMutation.data && (
          <div className="mt-3 rounded border border-neutral-100 bg-neutral-50 p-3 text-sm">
            <p className="text-neutral-700">
              Switched to primary. Status: {forcePrimaryMutation.data.status} |
              Active: {forcePrimaryMutation.data.active_url}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
