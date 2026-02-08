/**
 * Legislation admin types — Lex health, search, and detail.
 *
 * Source of truth: backend/src/yourai/api/routes/legislation_admin.py
 */

export interface LexOverviewResponse {
  status: "connected" | "fallback" | "error";
  active_url: string;
  primary_url: string;
  fallback_url: string;
  is_using_fallback: boolean;
  stats: LexStats | null;
}

export interface LexStats {
  [key: string]: number | string | undefined;
}

export interface LegislationSearchParams {
  query: string;
  year_from?: number;
  year_to?: number;
  legislation_type?: string[];
  offset?: number;
  limit?: number;
}

export interface LegislationSearchResultItem {
  [key: string]: unknown;
  title?: string;
  type?: string;
  year?: number;
  number?: number;
  category?: string;
  status?: string;
  description?: string;
  number_of_provisions?: number;
}

export interface LegislationSearchResponse {
  results: LegislationSearchResultItem[];
  total: number;
  offset: number;
  limit: number;
}

export interface LegislationDetailResponse {
  legislation: Record<string, unknown>;
  sections: Record<string, unknown>[];
  amendments: Record<string, unknown>[];
}

export interface HealthCheckResponse {
  primary_healthy: boolean;
  status: string;
  active_url: string;
}

export interface ForcePrimaryResponse {
  status: string;
  active_url: string;
}

// ---------------------------------------------------------------------------
// Self-hosted Qdrant status
// ---------------------------------------------------------------------------

export interface QdrantCollectionInfo {
  name: string;
  points_count: number;
  status: string;
}

export interface PrimaryStatusResponse {
  healthy: boolean;
  qdrant_url: string;
  collections: QdrantCollectionInfo[];
}

// ---------------------------------------------------------------------------
// Ingestion
// ---------------------------------------------------------------------------

export interface TriggerIngestionRequest {
  mode: "daily" | "full" | "amendments_led";
  years?: number[];
  limit?: number;
  pdf_fallback?: boolean;
}

// ---------------------------------------------------------------------------
// Indexed legislation
// ---------------------------------------------------------------------------

export interface IndexedLegislationItem {
  qdrant_point_id: string;
  legislation_id: string;
  title: string | null;
  type: string | null;
  year: number | null;
  number: number | null;
  category: string | null;
  status_text: string | null;
  section_count: number;
  uri: string | null;
  enactment_date: string | null;
}

export interface IndexedLegislationResponse {
  items: IndexedLegislationItem[];
  next_offset: string | null;
}

export interface RemoveLegislationRequest {
  legislation_ids: string[];
}

export interface RemoveLegislationResponse {
  removed: number;
  errors: string[];
}

export interface SyncIndexResponse {
  synced: number;
}

export interface TargetedIngestionRequest {
  types: string[];
  years: number[];
  limit?: number;
}

export interface IngestionJobResponse {
  id: string;
  tenant_id?: string;
  mode: string;
  status: "pending" | "running" | "completed" | "failed";
  triggered_by?: string;
  parameters: Record<string, unknown>;
  result?: Record<string, unknown> | null;
  error_message?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface IngestionJobListResponse {
  items: IngestionJobResponse[];
  total: number;
  offset: number;
  limit: number;
}
