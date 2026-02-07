"use client";

/**
 * Main App Shell Layout — Sidebar + Main Content
 */

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth/auth-context";
import { MessageSquare, FileText, Settings, LogOut } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function MainLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { user, isLoading, isAuthenticated, logout } = useAuth();
  const router = useRouter();

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push("/login");
    }
  }, [isLoading, isAuthenticated, router]);

  // Show loading while checking auth
  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-neutral-600">Loading...</div>
      </div>
    );
  }

  // Don't render if not authenticated (redirect in progress)
  if (!isAuthenticated) {
    return null;
  }

  return (
    <div className="flex h-screen overflow-hidden bg-neutral-50">
      {/* Sidebar */}
      <aside className="flex w-64 flex-col border-r border-neutral-200 bg-white">
        {/* Logo / Tenant Branding */}
        <div className="flex h-16 items-center border-b border-neutral-200 px-6">
          <h1 className="text-xl font-bold text-neutral-900">YourAI</h1>
        </div>

        {/* Navigation */}
        <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-4">
          <SidebarLink href="/conversations" icon={MessageSquare}>
            Conversations
          </SidebarLink>
          <SidebarLink href="/knowledge-base" icon={FileText}>
            Knowledge Base
          </SidebarLink>
          <SidebarLink href="/admin" icon={Settings}>
            Settings
          </SidebarLink>
        </nav>

        {/* User Menu */}
        <div className="border-t border-neutral-200 p-4">
          <div className="mb-2 text-sm">
            <div className="font-medium text-neutral-900">
              {user?.given_name} {user?.family_name}
            </div>
            <div className="text-neutral-500">{user?.email}</div>
          </div>
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
      <main className="flex-1 overflow-hidden">{children}</main>
    </div>
  );
}

/**
 * Sidebar Link Component
 */
function SidebarLink({
  href,
  icon: Icon,
  children,
}: {
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  children: React.ReactNode;
}) {
  return (
    <a
      href={href}
      className="flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium text-neutral-700 transition-colors hover:bg-neutral-100 hover:text-neutral-900"
    >
      <Icon className="h-5 w-5" />
      {children}
    </a>
  );
}
