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
