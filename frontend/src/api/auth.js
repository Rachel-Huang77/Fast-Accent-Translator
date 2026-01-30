// src/api/auth.js
// Uses unified API configuration
import { apiRequest } from '../config/api.js';

/**
 * Login with username + password
 */
export async function login({ username, password }) {
  const r = await apiRequest("/auth/login", { method: "POST", body: { username, password } });
  if (!r.ok) return r;
  const { user, accessToken } = r.data;
  return { ok: true, token: accessToken, user: { id: user.id, username: user.username, email: user.email ?? "", role: user.role } };
}

export async function logout() {
  // Call backend /auth/logout, delete Cookie
  const r = await apiRequest("/auth/logout", { method: "POST" });
  return r;  // Even if it fails, frontend will still clear state
}

/**
 * Register (backend)
 * - unique username
 * - unique email
 */
export async function register({ username, email, password }) {
  const r = await apiRequest("/auth/register", { method: "POST", body: { username, email, password } });
  if (!r.ok) return r;
  const { id, username: un, email: em } = r.data;
  return { ok: true, message: "Registration successful", user: { id, username: un, email: em || "" } };
}

/**
 * Check if username+email exists for password reset
 */
export async function checkUserForReset({ username, email }) {
  const r = await apiRequest("/auth/check-reset", { method: "POST", body: { username, email } });
  if (!r.ok) return r;
  return { ok: true, userId: r.data.userId };
}

/**
 * Reset password (after verification)
 */
export async function resetPassword({ userId, newPassword }) {
  const r = await apiRequest("/auth/reset-password", { method: "POST", body: { userId, newPassword } });
  return r.ok ? { ok: true, message: "Password updated successfully" } : r;
}

/**
 * Change password for logged-in user
 * Backend validates current user via Cookie/JWT, no userId needed
 */
export async function changePassword({ newPassword }) {
  const r = await apiRequest("/auth/change-password", { method: "POST", body: { newPassword } });
  return r.ok ? { ok: true } : r;
}
