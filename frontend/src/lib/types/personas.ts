/**
 * Persona types.
 *
 * Source of truth: API_CONTRACTS.md Section 6.7
 */

export interface PersonaResponse {
  id: string;
  tenant_id: string;
  name: string;
  description: string | null;
  system_instructions: string | null;
  activated_skills: Record<string, unknown>[];
  usage_count: number;
  created_at: string | null;
  updated_at: string | null;
}
