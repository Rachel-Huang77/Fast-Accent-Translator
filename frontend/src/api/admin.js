// frontend/src/api/admin.js
// Admin-related API endpoints

import { apiRequest } from '../config/api.js';

// ============================================================================
// 1. User Management APIs
// ============================================================================

/**
 * Get user list (with search and pagination)
 * @param {object} params - Query parameters
 * @param {string} [params.q] - Search keyword (username/email)
 * @param {number} [params.offset=0] - Pagination offset
 * @param {number} [params.limit=20] - Items per page
 * @returns {Promise<{ok: boolean, data?: {items: Array, offset: number, limit: number, total: number}}>}
 */
export async function listUsers({ q = '', offset = 0, limit = 20 } = {}) {
  const params = new URLSearchParams();
  if (q) params.append('q', q);
  params.append('offset', offset);
  params.append('limit', limit);

  return apiRequest(`/admin/users?${params.toString()}`);
}

/**
 * Get user details
 * @param {string} userId - User ID
 * @returns {Promise<{ok: boolean, data?: {user: object}}>}
 */
export async function getUserDetail(userId) {
  return apiRequest(`/admin/users/${userId}`);
}

/**
 * Update user information (Admin only)
 * @param {string} userId - User ID
 * @param {object} data - Update data
 * @param {string} [data.username] - New username
 * @param {string} [data.email] - New email
 * @param {string} [data.role] - New role (user/admin)
 * @returns {Promise<{ok: boolean, data?: {user: object}}>}
 */
export async function updateUser(userId, data) {
  return apiRequest(`/admin/users/${userId}`, {
    method: 'PATCH',
    body: data,
  });
}

/**
 * Delete user (Admin only)
 * @param {string} userId - User ID
 * @returns {Promise<{ok: boolean}>}
 */
export async function deleteUser(userId) {
  return apiRequest(`/admin/users/${userId}`, {
    method: 'DELETE',
  });
}

/**
 * Reset user password (Admin only)
 * @param {string} userId - User ID
 * @param {string} newPassword - New password
 * @returns {Promise<{ok: boolean}>}
 */
export async function resetUserPassword(userId, newPassword) {
  return apiRequest(`/admin/users/${userId}/reset-password`, {
    method: 'POST',
    body: { newPassword },
  });
}

// ============================================================================
// 2. License Key Management APIs
// ============================================================================

/**
 * Batch generate license keys
 * @param {object} params - Generation parameters
 * @param {number} params.count - Number of keys to generate (1-200)
 * @param {string} [params.keyType='paid'] - Key type
 * @param {number} [params.expireDays] - Expiry days (omit for permanent)
 * @param {string} [params.prefix='FAT'] - Key prefix
 * @returns {Promise<{ok: boolean, data?: {keys: Array<{id: string, key: string, keyType: string, expiresAt: string}>}}>}
 */
export async function batchGenerateKeys({ count, keyType = 'paid', expireDays, prefix = 'FAT' }) {
  return apiRequest('/admin/license-keys/batch', {
    method: 'POST',
    body: { count, keyType, expireDays, prefix },
  });
}

/**
 * Get license key list
 * @param {object} params - Query parameters
 * @param {boolean} [params.is_used] - Filter by used/unused
 * @param {string} [params.key_type] - Filter by key type
 * @param {number} [params.offset=0] - Pagination offset
 * @param {number} [params.limit=20] - Items per page
 * @returns {Promise<{ok: boolean, data?: {items: Array, offset: number, limit: number, total: number}}>}
 */
export async function listLicenseKeys({ is_used, key_type, offset = 0, limit = 20 } = {}) {
  const params = new URLSearchParams();
  if (is_used !== undefined) params.append('is_used', is_used);
  if (key_type) params.append('key_type', key_type);
  params.append('offset', offset);
  params.append('limit', limit);

  return apiRequest(`/admin/license-keys?${params.toString()}`);
}

/**
 * Get license key details
 * @param {string} keyId - Key ID
 * @returns {Promise<{ok: boolean, data?: object}>}
 */
export async function getLicenseKeyDetail(keyId) {
  return apiRequest(`/admin/license-keys/${keyId}`);
}

/**
 * Delete license key
 * @param {string} keyId - Key ID
 * @returns {Promise<{ok: boolean}>}
 */
export async function deleteLicenseKey(keyId) {
  return apiRequest(`/admin/license-keys/${keyId}`, {
    method: 'DELETE',
  });
}

/**
 * Verify license key (for regular users)
 * @param {string} key - Plain text key
 * @param {boolean} consume - Whether to consume the key (true to activate)
 * @returns {Promise<{ok: boolean, data?: {ok: boolean}}>}
 */
export async function verifyKey(key, consume = false) {
  return apiRequest('/admin/verify-key', {
    method: 'POST',
    body: { key, consume },
  });
}