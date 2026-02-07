"use client";

/**
 * User Management Page — Searchable user table with invite and edit.
 */

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/lib/auth/auth-context";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { SkeletonRow } from "@/components/ui/skeleton";
import { Search, Plus, UserPlus } from "lucide-react";
import { cn } from "@/lib/utils/cn";
import type { UserResponse } from "@/lib/types/users";
import type { UserStatus } from "@/lib/types/enums";
import type { CreateUser } from "@/lib/types/requests";

const statusColors: Record<UserStatus, string> = {
  active: "bg-green-100 text-green-700",
  pending: "bg-amber-100 text-amber-700",
  disabled: "bg-neutral-100 text-neutral-600",
  deleted: "bg-red-100 text-red-700",
};

export default function UsersPage() {
  const { api } = useAuth();
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [showInvite, setShowInvite] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["users", search],
    queryFn: () =>
      api.users.list({ page: 1, page_size: 50, search: search || undefined }),
  });

  const users = data?.items ?? [];

  return (
    <div className="flex h-full flex-col">
      {/* Toolbar */}
      <div className="flex items-center gap-3 border-b border-neutral-100 bg-white px-6 py-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-400" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search users..."
            className="pl-9"
          />
        </div>
        <Button onClick={() => setShowInvite(!showInvite)}>
          <UserPlus className="mr-2 h-4 w-4" />
          Invite User
        </Button>
      </div>

      {/* Invite form */}
      {showInvite && (
        <div className="border-b border-neutral-100 bg-neutral-50 px-6 py-4">
          <InviteForm
            onSuccess={() => {
              setShowInvite(false);
              queryClient.invalidateQueries({ queryKey: ["users"] });
            }}
          />
        </div>
      )}

      {/* Users table */}
      <div className="flex-1 overflow-y-auto">
        {isLoading ? (
          <div className="space-y-1">
            <SkeletonRow />
            <SkeletonRow />
            <SkeletonRow />
          </div>
        ) : users.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-neutral-500">
            <p>No users found</p>
          </div>
        ) : (
          <table className="w-full">
            <thead className="border-b border-neutral-200 bg-neutral-50 text-left text-xs font-medium uppercase text-neutral-500">
              <tr>
                <th className="px-6 py-3">Status</th>
                <th className="px-6 py-3">Name</th>
                <th className="px-6 py-3">Email</th>
                <th className="px-6 py-3">Roles</th>
                <th className="px-6 py-3">Last Active</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-100">
              {users.map((user) => (
                <UserRow key={user.id} user={user} />
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

function UserRow({ user }: { user: UserResponse }) {
  return (
    <tr className="hover:bg-neutral-50">
      <td className="px-6 py-3">
        <span
          className={cn(
            "rounded-full px-2 py-0.5 text-xs font-medium capitalize",
            statusColors[user.status],
          )}
        >
          {user.status}
        </span>
      </td>
      <td className="px-6 py-3 font-medium text-neutral-900">
        {user.given_name} {user.family_name}
      </td>
      <td className="px-6 py-3 text-sm text-neutral-600">{user.email}</td>
      <td className="px-6 py-3 text-sm text-neutral-600">
        {user.roles.map((r) => r.name).join(", ") || "—"}
      </td>
      <td className="px-6 py-3 text-sm text-neutral-500">
        {user.last_active_at
          ? new Date(user.last_active_at).toLocaleDateString()
          : "Never"}
      </td>
    </tr>
  );
}

function InviteForm({ onSuccess }: { onSuccess: () => void }) {
  const { api } = useAuth();
  const [email, setEmail] = useState("");
  const [givenName, setGivenName] = useState("");
  const [familyName, setFamilyName] = useState("");

  const createMutation = useMutation({
    mutationFn: (data: CreateUser) => api.users.create(data),
    onSuccess,
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !givenName || !familyName) return;
    createMutation.mutate({
      email,
      given_name: givenName,
      family_name: familyName,
    });
  };

  return (
    <form onSubmit={handleSubmit} className="flex items-end gap-3">
      <div>
        <label className="text-xs text-neutral-500">Email</label>
        <Input
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          type="email"
          required
          placeholder="user@example.com"
        />
      </div>
      <div>
        <label className="text-xs text-neutral-500">First Name</label>
        <Input
          value={givenName}
          onChange={(e) => setGivenName(e.target.value)}
          required
        />
      </div>
      <div>
        <label className="text-xs text-neutral-500">Last Name</label>
        <Input
          value={familyName}
          onChange={(e) => setFamilyName(e.target.value)}
          required
        />
      </div>
      <Button type="submit" disabled={createMutation.isPending}>
        <Plus className="mr-1 h-4 w-4" />
        Invite
      </Button>
    </form>
  );
}
