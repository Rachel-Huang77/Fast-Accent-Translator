// frontend/src/config/api.js
// Unified API configuration with environment variable support

/**
 * API Base URL
 * Uses environment variable VITE_API_BASE_URL, or defaults to localhost
 */
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * API v1 path prefix
 */
export const API_V1_PREFIX = '/api/v1';

/**
 * Complete API Base URL (with version prefix)
 */
export const API_BASE = `${API_BASE_URL}${API_V1_PREFIX}`;

/**
 * WebSocket URLs
 */
export const WS_BASE_URL = import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:8000';
export const WS_UPLOAD_URL = `${WS_BASE_URL}/ws/upload-audio`;
export const WS_TEXT_URL = `${WS_BASE_URL}/ws/asr-text`;
export const WS_TTS_URL = `${WS_BASE_URL}/ws/tts-audio`;

/**
 * Universal API request method
 * @param {string} path - API path (without base URL)
 * @param {object} options - Fetch options
 * @returns {Promise<{ok: boolean, data?: any, message?: string, code?: string}>}
 */


export async function apiRequest(
  path,
  { method = "GET", body, headers = {} } = {}
) {
  const url = `${API_BASE}${path}`;

  const fetchOptions = {
    method,
    credentials: "include", // Required: Let browser automatically include HttpOnly Cookie
    headers: {
      ...headers,
    },
  };

  if (body) {
    fetchOptions.headers["Content-Type"] = "application/json";
    fetchOptions.body = JSON.stringify(body);
  }

  try {
    const res = await fetch(url, fetchOptions);
    let data = null;

    try {
      data = await res.json();
    } catch {
      // Could be plain text / 204, ignore JSON parsing error
    }

    // =============== 🔥 Unified error code / detail extraction ============
    const detail = data?.detail;
    const errorCode =
      data?.error?.code ||
      (typeof detail === "object" ? detail?.code : undefined) ||
      data?.code;

    // =============== 🔥 Handle unauthenticated: AUTH_REQUIRED ============
    const isAuthRequired =
      res.status === 401 &&
      (
        detail === "AUTH_REQUIRED" ||              // Backend directly sets detail = "AUTH_REQUIRED"
        errorCode === "AUTH_REQUIRED"             // or detail/code/error.code = "AUTH_REQUIRED"
      );

    if (isAuthRequired) {
      console.warn("[api] AUTH_REQUIRED → redirect to /login");

      // Clear frontend login state
      localStorage.removeItem("authUserId");
      localStorage.removeItem("authUsername");
      localStorage.removeItem("authUserRole");

      // Force redirect to login page
      window.location.href = "/login";

      return { ok: false, message: "AUTH_REQUIRED", code: "AUTH_REQUIRED" };
    }

    // =============== 🔥 Handle unauthorized: admin only ============
    const isAdminOnly =
      res.status === 403 &&
      (
        detail === "ADMIN_ONLY" ||
        errorCode === "ADMIN_ONLY"
      );

    if (isAdminOnly) {
      console.warn("[api] ADMIN_ONLY → redirect to /dashboard");
      window.location.href = "/dashboard";
      return { ok: false, message: "ADMIN_ONLY", code: "ADMIN_ONLY" };
    }

    // =============== General error handling ==========================
    if (!res.ok || (data && data.success === false)) {
      const msg =
        data?.error?.message ||
        (typeof detail === "string" ? detail : detail?.message) ||
        `HTTP ${res.status}`;

      return {
        ok: false,
        message: msg,
        code: errorCode,
      };
    }

    // =============== Normal success return ==========================
    return { ok: true, data: data?.data ?? data };
  } catch (error) {
    return {
      ok: false,
      message: error.message || "Network error",
      code: "NETWORK_ERROR",
    };
  }
}
