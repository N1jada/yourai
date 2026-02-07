"use client";

/**
 * Admin Dashboard — Analytics overview with stat cards.
 */

import { BarChart3, Users, MessageSquare, Shield, TrendingUp } from "lucide-react";

export default function AdminDashboardPage() {
  // Placeholder stats — will connect to analytics endpoint when available
  const stats = [
    { label: "Total Users", value: "—", icon: Users },
    { label: "Conversations", value: "—", icon: MessageSquare },
    { label: "Policy Reviews", value: "—", icon: Shield },
    { label: "Avg Confidence", value: "—", icon: TrendingUp },
  ];

  return (
    <div className="overflow-y-auto p-6">
      <h1 className="text-2xl font-bold text-neutral-900">Dashboard</h1>
      <p className="mt-1 text-sm text-neutral-500">Organisation analytics overview</p>

      <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => (
          <div
            key={stat.label}
            className="rounded-lg border border-neutral-200 bg-white p-5"
          >
            <div className="flex items-center gap-3">
              <div className="rounded-md bg-neutral-100 p-2">
                <stat.icon className="h-5 w-5 text-neutral-600" />
              </div>
              <div>
                <p className="text-sm text-neutral-500">{stat.label}</p>
                <p className="text-2xl font-semibold text-neutral-900">{stat.value}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-8 rounded-lg border border-neutral-200 bg-white p-6">
        <div className="flex items-center gap-2 text-neutral-500">
          <BarChart3 className="h-5 w-5" />
          <span className="text-sm">Charts will appear here when the analytics API is available</span>
        </div>
      </div>
    </div>
  );
}
