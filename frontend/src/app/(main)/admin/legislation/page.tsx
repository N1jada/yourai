"use client";

/**
 * Legislation Admin Page — Lex health, browse, connection settings, and ingestion management.
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
  Database,
  Play,
  CheckCircle2,
  XCircle,
  Clock,
  Loader2,
  Trash2,
  Download,
  Filter,
} from "lucide-react";
import type {
  LegislationSearchResultItem,
  LegislationDetailResponse,
  IngestionJobResponse,
  PrimaryStatusResponse,
} from "@/lib/types/legislation";

type Tab = "overview" | "browse" | "indexed" | "ingestion" | "settings";

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

const jobStatusConfig: Record<
  string,
  { label: string; color: string; icon: typeof CheckCircle2 }
> = {
  pending: {
    label: "Pending",
    color: "bg-neutral-100 text-neutral-600",
    icon: Clock,
  },
  running: {
    label: "Running",
    color: "bg-blue-100 text-blue-700",
    icon: Loader2,
  },
  completed: {
    label: "Completed",
    color: "bg-green-100 text-green-700",
    icon: CheckCircle2,
  },
  failed: {
    label: "Failed",
    color: "bg-red-100 text-red-700",
    icon: XCircle,
  },
};

export default function LegislationAdminPage() {
  const [activeTab, setActiveTab] = useState<Tab>("overview");

  const tabs: { key: Tab; label: string }[] = [
    { key: "overview", label: "Overview" },
    { key: "browse", label: "Browse" },
    { key: "indexed", label: "Indexed" },
    { key: "ingestion", label: "Ingestion" },
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
        {activeTab === "indexed" && <IndexedSection />}
        {activeTab === "ingestion" && <IngestionSection />}
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

  const { data: primaryStatus, isLoading: primaryLoading } = useQuery({
    queryKey: ["admin-legislation-primary-status"],
    queryFn: () => api.legislation.getPrimaryStatus(),
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

      {/* Self-hosted Qdrant status */}
      <SelfHostedStatusCard
        primaryStatus={primaryStatus ?? null}
        isLoading={primaryLoading}
      />
    </div>
  );
}

function SelfHostedStatusCard({
  primaryStatus,
  isLoading,
}: {
  primaryStatus: PrimaryStatusResponse | null;
  isLoading: boolean;
}) {
  if (isLoading) {
    return <SkeletonCard />;
  }

  return (
    <div className="rounded-lg border border-neutral-200 bg-white p-5">
      <div className="flex items-center gap-3">
        <Database className="h-5 w-5 text-neutral-600" />
        <h3 className="font-semibold text-neutral-900">
          Self-Hosted Instance
        </h3>
        {primaryStatus && (
          <span
            className={cn(
              "rounded-full px-2.5 py-0.5 text-xs font-medium",
              primaryStatus.healthy
                ? "bg-green-100 text-green-700"
                : "bg-red-100 text-red-700",
            )}
          >
            {primaryStatus.healthy ? "Healthy" : "Unreachable"}
          </span>
        )}
      </div>

      {primaryStatus && (
        <div className="mt-3">
          <p className="text-xs text-neutral-500">
            Qdrant: <code className="text-xs">{primaryStatus.qdrant_url}</code>
          </p>

          {primaryStatus.collections.length > 0 ? (
            <div className="mt-3 overflow-hidden rounded border border-neutral-200">
              <table className="w-full">
                <thead className="border-b border-neutral-200 bg-neutral-50 text-left text-xs font-medium uppercase text-neutral-500">
                  <tr>
                    <th className="px-4 py-2">Collection</th>
                    <th className="px-4 py-2 text-right">Points</th>
                    <th className="px-4 py-2">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-neutral-100">
                  {primaryStatus.collections.map((col) => (
                    <tr key={col.name}>
                      <td className="px-4 py-2 text-sm font-medium text-neutral-900">
                        {col.name}
                      </td>
                      <td className="px-4 py-2 text-right text-sm tabular-nums text-neutral-600">
                        {col.points_count.toLocaleString()}
                      </td>
                      <td className="px-4 py-2 text-sm">
                        <span
                          className={cn(
                            "rounded-full px-2 py-0.5 text-xs font-medium",
                            col.status === "ok" || col.status === "green"
                              ? "bg-green-100 text-green-700"
                              : "bg-neutral-100 text-neutral-600",
                          )}
                        >
                          {col.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="mt-3 text-sm text-neutral-400">
              No collections found
            </p>
          )}
        </div>
      )}

      {!primaryStatus && (
        <p className="mt-3 text-sm text-neutral-400">
          Could not connect to self-hosted Qdrant instance.
        </p>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Browse
// ---------------------------------------------------------------------------

function BrowseSection() {
  const { api } = useAuth();
  const queryClient = useQueryClient();
  const [query, setQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [yearFrom, setYearFrom] = useState("");
  const [yearTo, setYearTo] = useState("");
  const [offset, setOffset] = useState(0);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [selectedItems, setSelectedItems] = useState<Set<string>>(new Set());
  const [showIngestConfirm, setShowIngestConfirm] = useState(false);

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

  const ingestMutation = useMutation({
    mutationFn: (params: { types: string[]; years: number[] }) =>
      api.legislation.triggerTargetedIngestion({
        types: params.types,
        years: params.years,
      }),
    onSuccess: () => {
      setSelectedItems(new Set());
      setShowIngestConfirm(false);
      queryClient.invalidateQueries({
        queryKey: ["admin-legislation-ingestion-jobs"],
      });
    },
  });

  const results = data?.results ?? [];

  const toggleSelect = (itemKey: string) => {
    setSelectedItems((prev) => {
      const next = new Set(prev);
      if (next.has(itemKey)) {
        next.delete(itemKey);
      } else {
        next.add(itemKey);
      }
      return next;
    });
  };

  // Group selected items by type+year for the confirmation
  const groupedSelection = (() => {
    const groups: Record<string, Set<number>> = {};
    for (const key of selectedItems) {
      const parts = key.split("-");
      const type = parts[0];
      const year = parseInt(parts[1], 10);
      if (!groups[type]) groups[type] = new Set();
      groups[type].add(year);
    }
    return groups;
  })();

  const handleIngest = () => {
    const types = Object.keys(groupedSelection);
    const years = new Set<number>();
    for (const yearSet of Object.values(groupedSelection)) {
      for (const y of yearSet) years.add(y);
    }
    ingestMutation.mutate({ types, years: [...years] });
  };

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
                  <th className="w-10 px-4 py-3" />
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
                  const selectionKey = `${String(item.type)}-${String(item.year)}-${String(item.number)}`;
                  const isExpanded = expandedId === itemId;
                  const isSelected = selectedItems.has(selectionKey);

                  return (
                    <ResultRow
                      key={itemId}
                      item={item}
                      isExpanded={isExpanded}
                      isSelected={isSelected}
                      onToggle={() =>
                        setExpandedId(isExpanded ? null : itemId)
                      }
                      onSelect={() => toggleSelect(selectionKey)}
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

      {/* Floating action bar for selected items */}
      {selectedItems.size > 0 && (
        <div className="sticky bottom-4 flex items-center justify-between rounded-lg border border-neutral-200 bg-white p-4 shadow-lg">
          <span className="text-sm font-medium text-neutral-700">
            {selectedItems.size} item{selectedItems.size !== 1 ? "s" : ""} selected
          </span>
          <div className="flex gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setSelectedItems(new Set())}
            >
              Clear
            </Button>
            <Button
              size="sm"
              onClick={() => setShowIngestConfirm(true)}
            >
              <Download className="mr-2 h-4 w-4" />
              Ingest Selected
            </Button>
          </div>
        </div>
      )}

      {/* Ingest confirmation dialog */}
      {showIngestConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="mx-4 max-w-md rounded-lg bg-white p-6 shadow-xl">
            <h3 className="text-lg font-semibold text-neutral-900">
              Confirm Targeted Ingestion
            </h3>
            <p className="mt-2 text-sm text-neutral-600">
              The Lex CLI ingests by type and year. Selecting individual items
              will ingest <strong>all legislation</strong> of that type for those years.
            </p>
            <div className="mt-3 space-y-1">
              {Object.entries(groupedSelection).map(([type, years]) => (
                <p key={type} className="text-sm text-neutral-700">
                  <span className="font-medium">{type.toUpperCase()}</span>{" "}
                  {[...years].sort().join(", ")} (all acts)
                </p>
              ))}
            </div>
            <div className="mt-4 flex justify-end gap-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowIngestConfirm(false)}
              >
                Cancel
              </Button>
              <Button
                size="sm"
                onClick={handleIngest}
                disabled={ingestMutation.isPending}
              >
                {ingestMutation.isPending ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <Play className="mr-2 h-4 w-4" />
                )}
                Start Ingestion
              </Button>
            </div>
            {ingestMutation.isError && (
              <p className="mt-2 text-sm text-red-600">Failed to trigger ingestion</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function ResultRow({
  item,
  isExpanded,
  isSelected,
  onToggle,
  onSelect,
}: {
  item: LegislationSearchResultItem;
  isExpanded: boolean;
  isSelected: boolean;
  onToggle: () => void;
  onSelect: () => void;
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
        <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
          <input
            type="checkbox"
            checked={isSelected}
            onChange={onSelect}
            className="rounded border-neutral-300"
            aria-label={`Select ${item.title ?? "legislation"}`}
          />
        </td>
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
          <td colSpan={8} className="bg-neutral-50 px-6 py-4">
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
// Indexed
// ---------------------------------------------------------------------------

function IndexedSection() {
  const { api } = useAuth();
  const queryClient = useQueryClient();
  const [typeFilter, setTypeFilter] = useState("");
  const [yearFilter, setYearFilter] = useState("");
  const [offsetId, setOffsetId] = useState<string | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  const { data, isLoading } = useQuery({
    queryKey: [
      "admin-legislation-indexed",
      typeFilter,
      yearFilter,
      offsetId,
    ],
    queryFn: () =>
      api.legislation.getIndexed({
        type_filter: typeFilter || undefined,
        year_filter: yearFilter ? parseInt(yearFilter, 10) : undefined,
        limit: 20,
        offset_id: offsetId ?? undefined,
      }),
  });

  const syncMutation = useMutation({
    mutationFn: () => api.legislation.syncIndex(),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["admin-legislation-indexed"],
      });
    },
  });

  const removeMutation = useMutation({
    mutationFn: (ids: string[]) =>
      api.legislation.removeIndexed({ legislation_ids: ids }),
    onSuccess: () => {
      setSelectedIds(new Set());
      queryClient.invalidateQueries({
        queryKey: ["admin-legislation-indexed"],
      });
    },
  });

  const items = data?.items ?? [];

  const toggleSelect = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const toggleAll = () => {
    if (selectedIds.size === items.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(items.map((i) => i.legislation_id)));
    }
  };

  return (
    <div className="space-y-4">
      {/* Filter bar */}
      <div className="flex flex-wrap items-end gap-3">
        <div className="w-40">
          <label className="text-xs text-neutral-500">Type</label>
          <select
            value={typeFilter}
            onChange={(e) => {
              setTypeFilter(e.target.value);
              setOffsetId(null);
            }}
            className="mt-1 w-full rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-900 focus:border-neutral-500 focus:outline-none focus:ring-1 focus:ring-neutral-500"
          >
            <option value="">All types</option>
            <option value="ukpga">UKPGA</option>
            <option value="uksi">UKSI</option>
            <option value="asp">ASP</option>
            <option value="asc">ASC</option>
            <option value="anaw">ANAW</option>
            <option value="nia">NIA</option>
            <option value="ssi">SSI</option>
            <option value="wsi">WSI</option>
            <option value="nisr">NISR</option>
          </select>
        </div>
        <div className="w-28">
          <label className="text-xs text-neutral-500">Year</label>
          <Input
            type="number"
            min={1800}
            max={2099}
            placeholder="Any"
            value={yearFilter}
            onChange={(e) => {
              setYearFilter(e.target.value);
              setOffsetId(null);
            }}
          />
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => syncMutation.mutate()}
          disabled={syncMutation.isPending}
        >
          {syncMutation.isPending ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <RefreshCw className="mr-2 h-4 w-4" />
          )}
          Sync from Qdrant
        </Button>
        {syncMutation.isSuccess && (
          <span className="text-sm text-green-600">
            Synced {syncMutation.data?.synced ?? 0} items
          </span>
        )}
      </div>

      {/* Table */}
      {isLoading && (
        <div className="space-y-2">
          <SkeletonCard />
          <SkeletonCard />
        </div>
      )}

      {!isLoading && items.length === 0 && (
        <div className="flex flex-col items-center py-12 text-neutral-500">
          <Database className="h-12 w-12" />
          <p className="mt-4">No legislation indexed in Qdrant</p>
          <p className="text-sm">Use the Ingestion tab or sync to populate.</p>
        </div>
      )}

      {items.length > 0 && (
        <>
          <div className="overflow-hidden rounded-lg border border-neutral-200 bg-white">
            <table className="w-full">
              <thead className="border-b border-neutral-200 bg-neutral-50 text-left text-xs font-medium uppercase text-neutral-500">
                <tr>
                  <th className="w-10 px-4 py-3">
                    <input
                      type="checkbox"
                      checked={selectedIds.size === items.length && items.length > 0}
                      onChange={toggleAll}
                      className="rounded border-neutral-300"
                      aria-label="Select all"
                    />
                  </th>
                  <th className="px-4 py-3">Title</th>
                  <th className="px-4 py-3">Type</th>
                  <th className="px-4 py-3">Year</th>
                  <th className="px-4 py-3">Number</th>
                  <th className="px-4 py-3">Sections</th>
                  <th className="px-4 py-3">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-100">
                {items.map((item) => (
                  <tr key={item.legislation_id} className="hover:bg-neutral-50">
                    <td className="px-4 py-3">
                      <input
                        type="checkbox"
                        checked={selectedIds.has(item.legislation_id)}
                        onChange={() => toggleSelect(item.legislation_id)}
                        className="rounded border-neutral-300"
                        aria-label={`Select ${item.title ?? item.legislation_id}`}
                      />
                    </td>
                    <td className="max-w-sm px-4 py-3 text-sm font-medium text-neutral-900">
                      {item.title ?? item.legislation_id}
                    </td>
                    <td className="px-4 py-3 text-sm text-neutral-600">
                      {item.type ? item.type.toUpperCase() : "\u2014"}
                    </td>
                    <td className="px-4 py-3 text-sm text-neutral-600">
                      {item.year ?? "\u2014"}
                    </td>
                    <td className="px-4 py-3 text-sm text-neutral-600">
                      {item.number ?? "\u2014"}
                    </td>
                    <td className="px-4 py-3 text-sm tabular-nums text-neutral-600">
                      {item.section_count}
                    </td>
                    <td className="px-4 py-3">
                      <button
                        onClick={() =>
                          removeMutation.mutate([item.legislation_id])
                        }
                        className="text-red-500 hover:text-red-700"
                        title="Remove from Qdrant"
                        aria-label={`Remove ${item.title ?? item.legislation_id}`}
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Cursor pagination */}
          {data?.next_offset && (
            <div className="text-center">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setOffsetId(data.next_offset)}
              >
                Load more
              </Button>
            </div>
          )}
        </>
      )}

      {/* Floating toolbar for bulk remove */}
      {selectedIds.size > 0 && (
        <div className="sticky bottom-4 flex items-center justify-between rounded-lg border border-neutral-200 bg-white p-4 shadow-lg">
          <span className="text-sm font-medium text-neutral-700">
            {selectedIds.size} item{selectedIds.size !== 1 ? "s" : ""} selected
          </span>
          <div className="flex gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setSelectedIds(new Set())}
            >
              Clear
            </Button>
            <Button
              variant="destructive"
              size="sm"
              onClick={() => removeMutation.mutate([...selectedIds])}
              disabled={removeMutation.isPending}
            >
              {removeMutation.isPending ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Trash2 className="mr-2 h-4 w-4" />
              )}
              Remove Selected ({selectedIds.size})
            </Button>
          </div>
        </div>
      )}

      {removeMutation.isError && (
        <p className="text-sm text-red-600">Failed to remove legislation</p>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Ingestion
// ---------------------------------------------------------------------------

function IngestionSection() {
  const { api } = useAuth();
  const queryClient = useQueryClient();
  const [mode, setMode] = useState<"daily" | "full" | "amendments_led">("daily");
  const [yearsInput, setYearsInput] = useState("");
  const [limitInput, setLimitInput] = useState("");
  const [pdfFallback, setPdfFallback] = useState(false);
  const [expandedJobId, setExpandedJobId] = useState<string | null>(null);

  const { data: jobs, isLoading: jobsLoading } = useQuery({
    queryKey: ["admin-legislation-ingestion-jobs"],
    queryFn: () => api.legislation.getIngestionJobs(20, 0),
    refetchInterval: 5000, // Poll for updates
  });

  const triggerMutation = useMutation({
    mutationFn: () => {
      const years = yearsInput
        .split(",")
        .map((y) => parseInt(y.trim(), 10))
        .filter((y) => !isNaN(y));
      const limit = limitInput ? parseInt(limitInput, 10) : undefined;

      return api.legislation.triggerIngestion({
        mode,
        years: years.length > 0 ? years : undefined,
        limit: limit && !isNaN(limit) ? limit : undefined,
        pdf_fallback: pdfFallback,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["admin-legislation-ingestion-jobs"],
      });
    },
  });

  const jobList = jobs?.items ?? [];

  return (
    <div className="space-y-6">
      {/* Trigger form */}
      <div className="rounded-lg border border-neutral-200 bg-white p-5">
        <div className="flex items-center gap-2">
          <Play className="h-5 w-5 text-neutral-600" />
          <h3 className="font-semibold text-neutral-900">
            Trigger Ingestion
          </h3>
        </div>

        <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div>
            <label className="text-xs font-medium text-neutral-500">Mode</label>
            <select
              value={mode}
              onChange={(e) => setMode(e.target.value as typeof mode)}
              className="mt-1 w-full rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-900 focus:border-neutral-500 focus:outline-none focus:ring-1 focus:ring-neutral-500"
            >
              <option value="daily">Daily</option>
              <option value="full">Full</option>
              <option value="amendments_led">Amendments-Led</option>
            </select>
          </div>

          <div>
            <label className="text-xs font-medium text-neutral-500">
              Years (comma-separated)
            </label>
            <Input
              className="mt-1"
              placeholder="2024, 2025"
              value={yearsInput}
              onChange={(e) => setYearsInput(e.target.value)}
            />
          </div>

          <div>
            <label className="text-xs font-medium text-neutral-500">Limit</label>
            <Input
              className="mt-1"
              type="number"
              min={1}
              placeholder="No limit"
              value={limitInput}
              onChange={(e) => setLimitInput(e.target.value)}
            />
          </div>

          <div className="flex items-end gap-3">
            <label className="flex items-center gap-2 text-sm text-neutral-600">
              <input
                type="checkbox"
                checked={pdfFallback}
                onChange={(e) => setPdfFallback(e.target.checked)}
                className="rounded border-neutral-300"
              />
              PDF fallback
            </label>
          </div>
        </div>

        <div className="mt-4">
          <Button
            onClick={() => triggerMutation.mutate()}
            disabled={triggerMutation.isPending}
          >
            {triggerMutation.isPending ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Play className="mr-2 h-4 w-4" />
            )}
            Start Ingestion
          </Button>

          {triggerMutation.isSuccess && (
            <span className="ml-3 text-sm text-green-600">
              Job created successfully
            </span>
          )}
          {triggerMutation.isError && (
            <span className="ml-3 text-sm text-red-600">
              Failed to trigger ingestion
            </span>
          )}
        </div>
      </div>

      {/* Targeted Ingestion card */}
      <TargetedIngestionCard />

      {/* Jobs history */}
      <div className="rounded-lg border border-neutral-200 bg-white p-5">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold text-neutral-900">Job History</h3>
          <Button
            variant="ghost"
            size="sm"
            onClick={() =>
              queryClient.invalidateQueries({
                queryKey: ["admin-legislation-ingestion-jobs"],
              })
            }
          >
            <RefreshCw className="mr-1 h-3.5 w-3.5" />
            Refresh
          </Button>
        </div>

        {jobsLoading && (
          <div className="mt-4 space-y-2">
            <SkeletonCard />
            <SkeletonCard />
          </div>
        )}

        {!jobsLoading && jobList.length === 0 && (
          <p className="mt-4 text-sm text-neutral-400">
            No ingestion jobs yet. Use the form above to trigger one.
          </p>
        )}

        {jobList.length > 0 && (
          <div className="mt-4 overflow-hidden rounded border border-neutral-200">
            <table className="w-full">
              <thead className="border-b border-neutral-200 bg-neutral-50 text-left text-xs font-medium uppercase text-neutral-500">
                <tr>
                  <th className="px-4 py-2" />
                  <th className="px-4 py-2">Mode</th>
                  <th className="px-4 py-2">Status</th>
                  <th className="px-4 py-2">Started</th>
                  <th className="px-4 py-2">Duration</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-100">
                {jobList.map((job) => (
                  <JobRow
                    key={job.id}
                    job={job}
                    isExpanded={expandedJobId === job.id}
                    onToggle={() =>
                      setExpandedJobId(
                        expandedJobId === job.id ? null : job.id,
                      )
                    }
                  />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

function JobRow({
  job,
  isExpanded,
  onToggle,
}: {
  job: IngestionJobResponse;
  isExpanded: boolean;
  onToggle: () => void;
}) {
  const cfg = jobStatusConfig[job.status] ?? jobStatusConfig.pending;
  const StatusIcon = cfg.icon;

  const duration = (() => {
    if (!job.started_at) return "\u2014";
    const start = new Date(job.started_at);
    const end = job.completed_at ? new Date(job.completed_at) : new Date();
    const seconds = Math.round((end.getTime() - start.getTime()) / 1000);
    if (seconds < 60) return `${String(seconds)}s`;
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${String(minutes)}m ${String(remainingSeconds)}s`;
  })();

  const startedDisplay = job.started_at
    ? new Date(job.started_at).toLocaleString()
    : job.created_at
      ? new Date(job.created_at).toLocaleString()
      : "\u2014";

  return (
    <>
      <tr
        className="cursor-pointer hover:bg-neutral-50"
        onClick={onToggle}
      >
        <td className="px-4 py-2">
          {isExpanded ? (
            <ChevronDown className="h-4 w-4 text-neutral-400" />
          ) : (
            <ChevronRight className="h-4 w-4 text-neutral-400" />
          )}
        </td>
        <td className="px-4 py-2 text-sm font-medium capitalize text-neutral-900">
          {job.mode.replace(/_/g, " ")}
        </td>
        <td className="px-4 py-2">
          <span
            className={cn(
              "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium",
              cfg.color,
            )}
          >
            <StatusIcon className={cn("h-3 w-3", job.status === "running" && "animate-spin")} />
            {cfg.label}
          </span>
        </td>
        <td className="px-4 py-2 text-sm text-neutral-600">{startedDisplay}</td>
        <td className="px-4 py-2 text-sm tabular-nums text-neutral-600">
          {duration}
        </td>
      </tr>

      {isExpanded && (
        <tr>
          <td colSpan={5} className="bg-neutral-50 px-6 py-4">
            <JobDetail job={job} />
          </td>
        </tr>
      )}
    </>
  );
}

function JobDetail({ job }: { job: IngestionJobResponse }) {
  return (
    <div className="space-y-3 text-sm">
      {/* Parameters */}
      {Object.keys(job.parameters).length > 0 && (
        <div>
          <h4 className="text-xs font-medium uppercase text-neutral-500">
            Parameters
          </h4>
          <pre className="mt-1 rounded bg-neutral-100 p-2 text-xs text-neutral-700">
            {JSON.stringify(job.parameters, null, 2)}
          </pre>
        </div>
      )}

      {/* Result */}
      {job.result && (
        <div>
          <h4 className="text-xs font-medium uppercase text-neutral-500">
            Result
          </h4>
          <pre className="mt-1 rounded bg-neutral-100 p-2 text-xs text-neutral-700">
            {JSON.stringify(job.result, null, 2)}
          </pre>
        </div>
      )}

      {/* Error */}
      {job.error_message && (
        <div>
          <h4 className="text-xs font-medium uppercase text-red-500">
            Error
          </h4>
          <pre className="mt-1 rounded bg-red-50 p-2 text-xs text-red-700 whitespace-pre-wrap">
            {job.error_message}
          </pre>
        </div>
      )}

      {/* Metadata */}
      <div className="grid gap-2 text-xs text-neutral-500 sm:grid-cols-2">
        <div>Job ID: <code>{job.id}</code></div>
        {job.created_at && <div>Created: {new Date(job.created_at).toLocaleString()}</div>}
        {job.completed_at && <div>Completed: {new Date(job.completed_at).toLocaleString()}</div>}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Targeted Ingestion
// ---------------------------------------------------------------------------

const LEGISLATION_TYPE_GROUPS = {
  Primary: ["ukpga", "asp", "asc", "anaw", "nia"],
  Secondary: ["uksi", "ssi", "wsi", "nisr"],
} as const;

function TargetedIngestionCard() {
  const { api } = useAuth();
  const queryClient = useQueryClient();
  const [selectedTypes, setSelectedTypes] = useState<Set<string>>(new Set());
  const [yearFrom, setYearFrom] = useState("");
  const [yearTo, setYearTo] = useState("");
  const [limit, setLimit] = useState("");

  const toggleType = (t: string) => {
    setSelectedTypes((prev) => {
      const next = new Set(prev);
      if (next.has(t)) {
        next.delete(t);
      } else {
        next.add(t);
      }
      return next;
    });
  };

  const years = (() => {
    const from = yearFrom ? parseInt(yearFrom, 10) : null;
    const to = yearTo ? parseInt(yearTo, 10) : null;
    if (from && to && from <= to) {
      const result: number[] = [];
      for (let y = from; y <= to; y++) result.push(y);
      return result;
    }
    if (from && !to) return [from];
    if (!from && to) return [to];
    return [];
  })();

  const canSubmit = selectedTypes.size > 0 && years.length > 0;

  const mutation = useMutation({
    mutationFn: () =>
      api.legislation.triggerTargetedIngestion({
        types: [...selectedTypes],
        years,
        limit: limit ? parseInt(limit, 10) : undefined,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["admin-legislation-ingestion-jobs"],
      });
    },
  });

  return (
    <div className="rounded-lg border border-neutral-200 bg-white p-5">
      <div className="flex items-center gap-2">
        <Filter className="h-5 w-5 text-neutral-600" />
        <h3 className="font-semibold text-neutral-900">
          Targeted Ingestion
        </h3>
      </div>
      <p className="mt-1 text-sm text-neutral-500">
        Ingest specific legislation types and years via the Lex CLI.
      </p>

      {/* Type selection */}
      <div className="mt-4 space-y-3">
        {Object.entries(LEGISLATION_TYPE_GROUPS).map(([group, types]) => (
          <div key={group}>
            <p className="text-xs font-medium uppercase text-neutral-500">{group}</p>
            <div className="mt-1 flex flex-wrap gap-2">
              {types.map((t) => (
                <label
                  key={t}
                  className={cn(
                    "flex cursor-pointer items-center gap-1.5 rounded-md border px-3 py-1.5 text-sm transition-colors",
                    selectedTypes.has(t)
                      ? "border-neutral-900 bg-neutral-900 text-white"
                      : "border-neutral-200 text-neutral-700 hover:bg-neutral-50",
                  )}
                >
                  <input
                    type="checkbox"
                    checked={selectedTypes.has(t)}
                    onChange={() => toggleType(t)}
                    className="sr-only"
                  />
                  {t.toUpperCase()}
                </label>
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* Year range */}
      <div className="mt-4 grid gap-4 sm:grid-cols-3">
        <div>
          <label className="text-xs font-medium text-neutral-500">Year from</label>
          <Input
            className="mt-1"
            type="number"
            min={1800}
            max={2099}
            placeholder="2020"
            value={yearFrom}
            onChange={(e) => setYearFrom(e.target.value)}
          />
        </div>
        <div>
          <label className="text-xs font-medium text-neutral-500">Year to</label>
          <Input
            className="mt-1"
            type="number"
            min={1800}
            max={2099}
            placeholder="2025"
            value={yearTo}
            onChange={(e) => setYearTo(e.target.value)}
          />
        </div>
        <div>
          <label className="text-xs font-medium text-neutral-500">Limit (optional)</label>
          <Input
            className="mt-1"
            type="number"
            min={1}
            placeholder="No limit"
            value={limit}
            onChange={(e) => setLimit(e.target.value)}
          />
        </div>
      </div>

      {/* Preview */}
      {canSubmit && (
        <div className="mt-3 rounded border border-neutral-100 bg-neutral-50 p-3 text-sm text-neutral-600">
          Will ingest all{" "}
          <span className="font-medium">
            [{[...selectedTypes].map((t) => t.toUpperCase()).join(", ")}]
          </span>{" "}
          from {years[0]} to {years[years.length - 1]}
          {limit ? ` (limit: ${limit})` : ""}
        </div>
      )}

      <div className="mt-4">
        <Button
          onClick={() => mutation.mutate()}
          disabled={!canSubmit || mutation.isPending}
        >
          {mutation.isPending ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <Play className="mr-2 h-4 w-4" />
          )}
          Start Targeted Ingestion
        </Button>
        {mutation.isSuccess && (
          <span className="ml-3 text-sm text-green-600">
            Job created successfully
          </span>
        )}
        {mutation.isError && (
          <span className="ml-3 text-sm text-red-600">
            Failed to trigger ingestion
          </span>
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
