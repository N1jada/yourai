"use client";

/**
 * Main App Shell Layout — Sidebar + Main Content
 */

import { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth/auth-context";
import { useSidebarStore } from "@/stores/sidebar-store";
import { useTenantBranding } from "@/lib/hooks/use-tenant-branding";
import {
  MessageSquare,
  FileText,
  Shield,
  Settings,
  LogOut,
  User,
  Menu,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils/cn";

export default function MainLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { user, isLoading, isAuthenticated, logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const { isOpen, toggle, close } = useSidebarStore();
  const { appName, logoUrl } = useTenantBranding();

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push("/login");
    }
  }, [isLoading, isAuthenticated, router]);

  // Close sidebar on mobile when navigating
  useEffect(() => {
    if (window.innerWidth < 768) {
      close();
    }
  }, [pathname, close]);

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-neutral-600">Loading...</div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  return (
    <div className="flex h-screen overflow-hidden bg-neutral-50">
      {/* Mobile overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 z-20 bg-black/50 md:hidden"
          onClick={close}
          aria-hidden="true"
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-30 flex w-64 flex-col border-r border-neutral-200 bg-white transition-transform md:static md:translate-x-0",
          isOpen ? "translate-x-0" : "-translate-x-full",
        )}
      >
        {/* Logo / Tenant Branding */}
        <div className="flex h-16 items-center justify-between border-b border-neutral-200 px-6">
          <div className="flex items-center gap-2">
            {logoUrl && (
              <img src={logoUrl} alt="" className="h-8 w-8 rounded" aria-hidden="true" />
            )}
            <h1 className="text-xl font-bold text-neutral-900">{appName}</h1>
          </div>
          <Button
            variant="ghost"
            size="sm"
            className="md:hidden"
            onClick={close}
            aria-label="Close sidebar"
          >
            <X className="h-5 w-5" />
          </Button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-4" aria-label="Main navigation">
          <SidebarLink href="/conversations" icon={MessageSquare} active={pathname.startsWith("/conversations")}>
            Conversations
          </SidebarLink>
          <SidebarLink href="/knowledge-base" icon={FileText} active={pathname.startsWith("/knowledge-base")}>
            Knowledge Base
          </SidebarLink>
          <SidebarLink href="/policy-review" icon={Shield} active={pathname.startsWith("/policy-review")}>
            Policy Review
          </SidebarLink>
          <SidebarLink href="/admin" icon={Settings} active={pathname.startsWith("/admin")}>
            Admin
          </SidebarLink>
        </nav>

        {/* User Menu */}
        <div className="border-t border-neutral-200 p-4">
          <a
            href="/profile"
            className="mb-2 flex items-center gap-2 rounded-md p-1 text-sm hover:bg-neutral-100"
          >
            <User className="h-4 w-4 text-neutral-400" />
            <div className="min-w-0 flex-1">
              <div className="truncate font-medium text-neutral-900">
                {user?.given_name} {user?.family_name}
              </div>
              <div className="truncate text-neutral-500">{user?.email}</div>
            </div>
          </a>
          <Button
            variant="ghost"
            size="sm"
            className="w-full justify-start"
            onClick={() => logout()}
          >
            <LogOut className="mr-2 h-4 w-4" />
            Sign out
          </Button>
        </div>
      </aside>

      {/* Main Content */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Mobile header */}
        <header className="flex h-12 items-center border-b border-neutral-200 bg-white px-4 md:hidden">
          <Button
            variant="ghost"
            size="sm"
            onClick={toggle}
            aria-label="Open sidebar"
          >
            <Menu className="h-5 w-5" />
          </Button>
          <span className="ml-3 font-semibold text-neutral-900">{appName}</span>
        </header>

        <main id="main-content" className="flex-1 overflow-hidden">{children}</main>
      </div>
    </div>
  );
}

/**
 * Sidebar Link Component with active state
 */
function SidebarLink({
  href,
  icon: Icon,
  active,
  children,
}: {
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  active: boolean;
  children: React.ReactNode;
}) {
  return (
    <a
      href={href}
      className={cn(
        "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
        active
          ? "bg-neutral-100 text-neutral-900"
          : "text-neutral-600 hover:bg-neutral-50 hover:text-neutral-900",
      )}
      aria-current={active ? "page" : undefined}
    >
      <Icon className="h-5 w-5" />
      {children}
    </a>
  );
}
