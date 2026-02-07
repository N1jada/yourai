/**
 * Health check types.
 *
 * Source of truth: API_CONTRACTS.md Section 6.14
 */

export interface HealthResponse {
  status: string;
  database: string;
  qdrant: string;
  redis: string;
  lex: string;
  version: string;
}
