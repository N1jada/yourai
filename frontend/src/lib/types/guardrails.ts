/**
 * Guardrail types.
 *
 * Source of truth: API_CONTRACTS.md Section 6.7
 */

import type { GuardrailStatus } from "./enums";

export interface GuardrailResponse {
  id: string;
  tenant_id: string;
  name: string;
  description: string | null;
  status: GuardrailStatus;
  configuration_rules: Record<string, unknown>;
  created_at: string | null;
  updated_at: string | null;
}
