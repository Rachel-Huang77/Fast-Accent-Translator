// src/api/dashboard.js
// Uses unified API configuration
import { apiRequest } from '../config/api.js';

/**
 * Verify and consume upgrade key (regular user activates paid model)
 * @param {string} key - Plain text key
 * @returns {Promise<{ok: boolean, message?: string}>}
 */
export async function verifyUpgradeKey(key) {
  // Call with consume=true to actually activate the key
  const result = await apiRequest('/admin/verify-key', {
    method: 'POST',
    body: { key, consume: true },
  });

  if (result.ok && result.data?.ok) {
    return { ok: true };
  } else {
    return { ok: false, message: result.message || 'Key invalid or already used' };
  }
}
