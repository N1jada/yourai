"use client";

/**
 * Profile Page — Edit personal details and notification preferences.
 */

import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/lib/auth/auth-context";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { SkeletonCard } from "@/components/ui/skeleton";
import { User, Save, Mail, BellRing } from "lucide-react";
import type { UpdateProfile } from "@/lib/types/requests";

export default function ProfilePage() {
  const { api, user: authUser } = useAuth();
  const queryClient = useQueryClient();

  const { data: profile, isLoading } = useQuery({
    queryKey: ["profile"],
    queryFn: () => api.profile.get(),
  });

  const [givenName, setGivenName] = useState("");
  const [familyName, setFamilyName] = useState("");
  const [jobRole, setJobRole] = useState("");
  const [emailNotifications, setEmailNotifications] = useState(true);
  const [policyAlerts, setPolicyAlerts] = useState(true);
  const [weeklyDigest, setWeeklyDigest] = useState(false);

  // Sync form when profile loads
  useEffect(() => {
    if (profile) {
      setGivenName(profile.given_name);
      setFamilyName(profile.family_name);
      setJobRole(profile.job_role ?? "");
      const prefs = profile.notification_preferences ?? {};
      setEmailNotifications(prefs.email_notifications !== false);
      setPolicyAlerts(prefs.policy_alerts !== false);
      setWeeklyDigest(prefs.weekly_digest === true);
    }
  }, [profile]);

  const updateMutation = useMutation({
    mutationFn: (data: UpdateProfile) => api.profile.update(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["profile"] });
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!givenName.trim() || !familyName.trim()) return;

    updateMutation.mutate({
      given_name: givenName.trim(),
      family_name: familyName.trim(),
      job_role: jobRole.trim() || undefined,
      notification_preferences: {
        email_notifications: emailNotifications,
        policy_alerts: policyAlerts,
        weekly_digest: weeklyDigest,
      },
    });
  };

  if (isLoading) {
    return (
      <div className="overflow-y-auto p-6">
        <SkeletonCard />
      </div>
    );
  }

  return (
    <div className="overflow-y-auto p-6">
      <div className="mx-auto max-w-2xl">
        <h1 className="text-2xl font-bold text-neutral-900">Profile</h1>
        <p className="mt-1 text-sm text-neutral-500">
          Manage your personal details and preferences
        </p>

        <form onSubmit={handleSubmit} className="mt-8 space-y-8">
          {/* Personal Information */}
          <section>
            <div className="mb-4 flex items-center gap-2">
              <User className="h-5 w-5 text-neutral-600" />
              <h2 className="text-lg font-semibold text-neutral-900">
                Personal Information
              </h2>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label className="text-xs font-medium text-neutral-500">
                  First Name
                </label>
                <Input
                  value={givenName}
                  onChange={(e) => setGivenName(e.target.value)}
                  required
                />
              </div>
              <div>
                <label className="text-xs font-medium text-neutral-500">
                  Last Name
                </label>
                <Input
                  value={familyName}
                  onChange={(e) => setFamilyName(e.target.value)}
                  required
                />
              </div>
              <div className="sm:col-span-2">
                <label className="text-xs font-medium text-neutral-500">
                  Job Role
                </label>
                <Input
                  value={jobRole}
                  onChange={(e) => setJobRole(e.target.value)}
                  placeholder="e.g. Compliance Officer"
                />
              </div>
            </div>
          </section>

          {/* Email (read-only) */}
          <section>
            <div className="mb-4 flex items-center gap-2">
              <Mail className="h-5 w-5 text-neutral-600" />
              <h2 className="text-lg font-semibold text-neutral-900">Email</h2>
            </div>
            <Input
              value={profile?.email ?? authUser?.email ?? ""}
              disabled
              className="max-w-sm bg-neutral-50"
            />
            <p className="mt-1 text-xs text-neutral-400">
              Contact your administrator to change your email address
            </p>
          </section>

          {/* Notification Preferences */}
          <section>
            <div className="mb-4 flex items-center gap-2">
              <BellRing className="h-5 w-5 text-neutral-600" />
              <h2 className="text-lg font-semibold text-neutral-900">
                Notifications
              </h2>
            </div>
            <div className="space-y-3">
              <label className="flex items-center gap-3">
                <input
                  type="checkbox"
                  checked={emailNotifications}
                  onChange={(e) => setEmailNotifications(e.target.checked)}
                  className="h-4 w-4 rounded border-neutral-300 text-brand-600 focus:ring-brand-500"
                />
                <div>
                  <p className="text-sm font-medium text-neutral-900">
                    Email Notifications
                  </p>
                  <p className="text-xs text-neutral-500">
                    Receive email updates about your conversations
                  </p>
                </div>
              </label>
              <label className="flex items-center gap-3">
                <input
                  type="checkbox"
                  checked={policyAlerts}
                  onChange={(e) => setPolicyAlerts(e.target.checked)}
                  className="h-4 w-4 rounded border-neutral-300 text-brand-600 focus:ring-brand-500"
                />
                <div>
                  <p className="text-sm font-medium text-neutral-900">
                    Policy Alerts
                  </p>
                  <p className="text-xs text-neutral-500">
                    Get notified about regulatory changes affecting your policies
                  </p>
                </div>
              </label>
              <label className="flex items-center gap-3">
                <input
                  type="checkbox"
                  checked={weeklyDigest}
                  onChange={(e) => setWeeklyDigest(e.target.checked)}
                  className="h-4 w-4 rounded border-neutral-300 text-brand-600 focus:ring-brand-500"
                />
                <div>
                  <p className="text-sm font-medium text-neutral-900">
                    Weekly Digest
                  </p>
                  <p className="text-xs text-neutral-500">
                    Receive a weekly summary of activity and updates
                  </p>
                </div>
              </label>
            </div>
          </section>

          {/* Save */}
          <div className="flex items-center gap-3">
            <Button type="submit" disabled={updateMutation.isPending}>
              <Save className="mr-2 h-4 w-4" />
              {updateMutation.isPending ? "Saving..." : "Save Changes"}
            </Button>
            {updateMutation.isSuccess && (
              <span className="text-sm text-green-600">
                Profile updated successfully
              </span>
            )}
            {updateMutation.isError && (
              <span className="text-sm text-red-600">
                Failed to update profile
              </span>
            )}
          </div>
        </form>
      </div>
    </div>
  );
}
