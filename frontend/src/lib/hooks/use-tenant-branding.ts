"use client";

/**
 * Tenant Branding Hook — Fetches tenant branding and applies CSS custom properties.
 */

import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@/lib/auth/auth-context";
import type { BrandingConfig } from "@/lib/types/tenant";

/**
 * Apply branding colour overrides as CSS custom properties.
 * The primary_colour/secondary_colour from BrandingConfig are applied to the
 * brand-600 CSS variable. HSL triplets expected (e.g. "221 83% 53%").
 */
function applyBrandingToDOM(branding: BrandingConfig) {
  const root = document.documentElement;

  if (branding.primary_colour) {
    root.style.setProperty("--brand-600", branding.primary_colour);
  }
  if (branding.secondary_colour) {
    root.style.setProperty("--brand-500", branding.secondary_colour);
  }
}

export function useTenantBranding() {
  const { api, isAuthenticated } = useAuth();

  const { data: config } = useQuery({
    queryKey: ["tenant-config"],
    queryFn: () => api.tenant.getConfig(),
    enabled: isAuthenticated,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  useEffect(() => {
    if (config?.branding) {
      applyBrandingToDOM(config.branding);
    }
  }, [config]);

  return {
    appName: config?.branding?.app_name ?? "YourAI",
    logoUrl: config?.branding?.logo_url ?? null,
  };
}
