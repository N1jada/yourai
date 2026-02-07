/**
 * API Client — Base HTTP client with auth token handling
 */

import type { ErrorResponse } from "@/lib/types/common";

export class ApiClientError extends Error {
  constructor(
    message: string,
    public statusCode?: number,
    public code?: string,
  ) {
    super(message);
    this.name = "ApiClientError";
  }
}

export class ApiClient {
  private baseUrl: string;
  private getToken: () => string | null;
  private onUnauthorized?: () => void;

  constructor(config: {
    baseUrl?: string;
    getToken: () => string | null;
    onUnauthorized?: () => void;
  }) {
    this.baseUrl = config.baseUrl || process.env.NEXT_PUBLIC_API_BASE_URL || "";
    this.getToken = config.getToken;
    this.onUnauthorized = config.onUnauthorized;
  }

  /**
   * Make an HTTP request with automatic auth header injection
   */
  private async request<T>(
    path: string,
    options: RequestInit = {},
  ): Promise<T> {
    const url = `${this.baseUrl}${path}`;
    const token = this.getToken();

    const headers: HeadersInit = {
      "Content-Type": "application/json",
      ...options.headers,
    };

    // Add auth header if token exists
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    try {
      const response = await fetch(url, {
        ...options,
        headers,
      });

      // Handle 401 Unauthorized
      if (response.status === 401) {
        this.onUnauthorized?.();
        throw new ApiClientError("Unauthorized", 401);
      }

      // Handle other error statuses
      if (!response.ok) {
        const errorData: ErrorResponse = await response.json().catch(() => ({
          code: "unknown",
          message: `HTTP ${response.status}: ${response.statusText}`,
        }));

        throw new ApiClientError(
          errorData.message,
          response.status,
          errorData.code,
        );
      }

      // Handle 204 No Content
      if (response.status === 204) {
        return undefined as T;
      }

      // Parse JSON response
      return await response.json();
    } catch (error) {
      if (error instanceof ApiClientError) {
        throw error;
      }

      // Network or parsing error
      throw new ApiClientError(
        error instanceof Error ? error.message : "Unknown error",
      );
    }
  }

  /**
   * GET request
   */
  async get<T>(path: string, params?: Record<string, unknown>): Promise<T> {
    const queryString = params
      ? "?" +
        new URLSearchParams(
          Object.entries(params)
            .filter(([, value]) => value !== undefined && value !== null)
            .map(([key, value]) => [key, String(value)]),
        ).toString()
      : "";

    return this.request<T>(path + queryString, {
      method: "GET",
    });
  }

  /**
   * POST request
   */
  async post<T>(path: string, body?: unknown): Promise<T> {
    return this.request<T>(path, {
      method: "POST",
      body: body ? JSON.stringify(body) : undefined,
    });
  }

  /**
   * PATCH request
   */
  async patch<T>(path: string, body?: unknown): Promise<T> {
    return this.request<T>(path, {
      method: "PATCH",
      body: body ? JSON.stringify(body) : undefined,
    });
  }

  /**
   * DELETE request
   */
  async delete<T>(path: string): Promise<T> {
    return this.request<T>(path, {
      method: "DELETE",
    });
  }

  /**
   * POST multipart/form-data (for file uploads)
   */
  async postFormData<T>(path: string, formData: FormData): Promise<T> {
    const url = `${this.baseUrl}${path}`;
    const token = this.getToken();

    const headers: HeadersInit = {};

    // Add auth header if token exists
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    // Note: Do NOT set Content-Type for FormData — browser sets it with boundary

    try {
      const response = await fetch(url, {
        method: "POST",
        headers,
        body: formData,
      });

      if (response.status === 401) {
        this.onUnauthorized?.();
        throw new ApiClientError("Unauthorized", 401);
      }

      if (!response.ok) {
        const errorData: ErrorResponse = await response.json().catch(() => ({
          code: "unknown",
          message: `HTTP ${response.status}: ${response.statusText}`,
        }));

        throw new ApiClientError(
          errorData.message,
          response.status,
          errorData.code,
        );
      }

      return await response.json();
    } catch (error) {
      if (error instanceof ApiClientError) {
        throw error;
      }

      throw new ApiClientError(
        error instanceof Error ? error.message : "Unknown error",
      );
    }
  }
}
