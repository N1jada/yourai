/**
 * Tenant & Auth types.
 *
 * Source of truth: API_CONTRACTS.md Section 6.3
 */

import type { SubscriptionTier } from "./enums";

export interface BrandingConfig {
  logo_url?: string;
  favicon_url?: string;
  app_name?: string;
  primary_colour?: string;
  secondary_colour?: string;
  custom_domain?: string;
  disclaimer_text?: string;
}

export interface AIConfig {
  confidence_thresholds?: Record<string, unknown>;
  topic_restrictions?: string[];
  model_overrides?: Record<string, unknown>;
}

export interface TenantConfig {
  id: string;
  name: string;
  slug: string;
  industry_vertical: string | null;
  branding: BrandingConfig;
  ai_config: AIConfig;
  subscription_tier: SubscriptionTier;
  credit_limit: number;
  billing_period_start: string | null;
  billing_period_end: string | null;
  is_active: boolean;
  news_feed_urls: string[];
  external_source_integrations: Record<string, unknown>[];
  vector_namespace: string | null;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  expires_in: number;
}
