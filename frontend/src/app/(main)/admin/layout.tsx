"use client";

/**
 * Admin Layout — Sub-navigation tabs for admin pages.
 */

import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils/cn";

const tabs = [
  { href: "/admin", label: "Dashboard" },
  { href: "/admin/users", label: "Users" },
  { href: "/admin/personas", label: "Personas" },
  { href: "/admin/guardrails", label: "Guardrails" },
  { href: "/admin/activity-log", label: "Activity Log" },
];

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();

  return (
    <div className="flex h-full flex-col">
      {/* Tabs */}
      <div className="border-b border-neutral-200 bg-white px-6">
        <nav className="flex gap-6" aria-label="Admin navigation">
          {tabs.map((tab) => {
            const isActive =
              tab.href === "/admin"
                ? pathname === "/admin"
                : pathname.startsWith(tab.href);

            return (
              <a
                key={tab.href}
                href={tab.href}
                className={cn(
                  "border-b-2 pb-3 pt-4 text-sm font-medium transition-colors",
                  isActive
                    ? "border-neutral-900 text-neutral-900"
                    : "border-transparent text-neutral-500 hover:border-neutral-300 hover:text-neutral-700",
                )}
                aria-current={isActive ? "page" : undefined}
              >
                {tab.label}
              </a>
            );
          })}
        </nav>
      </div>

      <div className="flex-1 overflow-hidden">{children}</div>
    </div>
  );
}
