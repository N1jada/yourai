"use client";

/**
 * Auth Context — Authentication state management
 */

import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { ApiClient } from "../api/client";
import { Api } from "../api/endpoints";
import type { UserResponse } from "@/lib/types/users";
import type { LoginRequest } from "@/lib/types/requests";
import { tokenStorage } from "./token-storage";

interface AuthContextValue {
  user: UserResponse | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (credentials: LoginRequest) => Promise<void>;
  logout: () => Promise<void>;
  api: Api;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  // Create API client with token getter and unauthorized handler
  const apiClient = React.useMemo(
    () =>
      new ApiClient({
        getToken: () => tokenStorage.getToken(),
        onUnauthorized: () => {
          tokenStorage.clearToken();
          setUser(null);
          router.push("/login");
        },
      }),
    [router],
  );

  const api = React.useMemo(() => new Api(apiClient), [apiClient]);

  /**
   * Load user from stored token on mount
   */
  useEffect(() => {
    const loadUser = async () => {
      const token = tokenStorage.getToken();

      if (!token) {
        setIsLoading(false);
        return;
      }

      try {
        const currentUser = await api.auth.getCurrentUser();
        setUser(currentUser);
      } catch (error) {
        console.error("Failed to load user:", error);
        tokenStorage.clearToken();
      } finally {
        setIsLoading(false);
      }
    };

    loadUser();
  }, [api]);

  /**
   * Login with email/password
   */
  const login = useCallback(
    async (credentials: LoginRequest) => {
      setIsLoading(true);
      try {
        const response = await api.auth.login(credentials);
        tokenStorage.setToken(response.access_token, response.expires_in);
        setUser(response.user);
        router.push("/conversations");
      } catch (error) {
        setIsLoading(false);
        throw error;
      }
    },
    [api, router],
  );

  /**
   * Logout
   */
  const logout = useCallback(async () => {
    try {
      await api.auth.logout();
    } catch (error) {
      console.error("Logout failed:", error);
    } finally {
      tokenStorage.clearToken();
      setUser(null);
      router.push("/login");
    }
  }, [api, router]);

  const value: AuthContextValue = {
    user,
    isLoading,
    isAuthenticated: !!user,
    login,
    logout,
    api,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

/**
 * Hook to access auth context
 */
export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
