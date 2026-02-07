/**
 * Token Storage — LocalStorage-based token persistence
 */

const ACCESS_TOKEN_KEY = "yourai_access_token";
const TOKEN_EXPIRY_KEY = "yourai_token_expiry";

export const tokenStorage = {
  /**
   * Store access token and expiry time
   */
  setToken(token: string, expiresIn: number): void {
    if (typeof window === "undefined") return;

    try {
      localStorage.setItem(ACCESS_TOKEN_KEY, token);
      const expiryTime = Date.now() + expiresIn * 1000;
      localStorage.setItem(TOKEN_EXPIRY_KEY, expiryTime.toString());
    } catch (error) {
      console.error("Failed to store token:", error);
    }
  },

  /**
   * Get access token (null if expired or missing)
   */
  getToken(): string | null {
    if (typeof window === "undefined") return null;

    try {
      const token = localStorage.getItem(ACCESS_TOKEN_KEY);
      const expiryTime = localStorage.getItem(TOKEN_EXPIRY_KEY);

      if (!token || !expiryTime) {
        return null;
      }

      // Check if token is expired
      if (Date.now() >= parseInt(expiryTime, 10)) {
        this.clearToken();
        return null;
      }

      return token;
    } catch (error) {
      console.error("Failed to retrieve token:", error);
      return null;
    }
  },

  /**
   * Clear stored token
   */
  clearToken(): void {
    if (typeof window === "undefined") return;

    try {
      localStorage.removeItem(ACCESS_TOKEN_KEY);
      localStorage.removeItem(TOKEN_EXPIRY_KEY);
    } catch (error) {
      console.error("Failed to clear token:", error);
    }
  },

  /**
   * Check if token exists and is not expired
   */
  hasValidToken(): boolean {
    return this.getToken() !== null;
  },
};
