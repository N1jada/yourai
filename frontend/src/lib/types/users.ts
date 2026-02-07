/**
 * User, Role, and Permission types.
 *
 * Source of truth: API_CONTRACTS.md Section 6.4
 */

import type { UserStatus } from "./enums";

export interface PermissionResponse {
  id: string;
  name: string;
  description: string | null;
}

export interface RoleResponse {
  id: string;
  tenant_id: string;
  name: string;
  description: string | null;
  permissions: PermissionResponse[];
  created_at: string | null;
}

export interface UserResponse {
  id: string;
  tenant_id: string;
  email: string;
  given_name: string;
  family_name: string;
  job_role: string | null;
  status: UserStatus;
  last_active_at: string | null;
  notification_preferences: Record<string, unknown>;
  roles: RoleResponse[];
  created_at: string | null;
  updated_at: string | null;
}

export interface BulkInviteResult {
  created: number;
  skipped: number;
  errors: Record<string, unknown>[];
}
