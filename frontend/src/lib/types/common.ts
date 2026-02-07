/**
 * Shared types — Pagination wrapper and error response.
 *
 * Source of truth: API_CONTRACTS.md Section 6.2
 */

/** Offset-based pagination wrapper. */
export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  has_next: boolean;
}

/** Standard error response body. */
export interface ErrorResponse {
  code: string;
  message: string;
  detail?: Record<string, unknown>;
}
