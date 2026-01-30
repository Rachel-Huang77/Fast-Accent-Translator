// tests/frontend/config/api.test.js
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { apiRequest, API_BASE } from '@src/config/api.js'

// Mock fetch globally
global.fetch = vi.fn()

// Mock window.location
const mockLocation = {
  href: '',
}
Object.defineProperty(window, 'location', {
  value: mockLocation,
  writable: true,
})

describe('apiRequest', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
    mockLocation.href = ''
    global.fetch.mockClear()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  // Happy cases
  describe('Successful requests', () => {
    it('should make GET request successfully', async () => {
      const mockData = { data: { id: 1, name: 'Test' } }
      global.fetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockData,
      })

      const result = await apiRequest('/test')

      expect(global.fetch).toHaveBeenCalledWith(
        `${API_BASE}/test`,
        expect.objectContaining({
          method: 'GET',
          credentials: 'include',
          headers: {},
        })
      )
      expect(result).toEqual({ ok: true, data: mockData.data })
    })

    it('should make POST request with body successfully', async () => {
      const mockData = { data: { id: 1 } }
      const requestBody = { username: 'test', password: 'pass123' }
      
      global.fetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockData,
      })

      const result = await apiRequest('/test', {
        method: 'POST',
        body: requestBody,
      })

      expect(global.fetch).toHaveBeenCalledWith(
        `${API_BASE}/test`,
        expect.objectContaining({
          method: 'POST',
          credentials: 'include',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(requestBody),
        })
      )
      expect(result).toEqual({ ok: true, data: mockData.data })
    })

    it('should handle response without data property', async () => {
      const mockData = { id: 1, name: 'Test' }
      global.fetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockData,
      })

      const result = await apiRequest('/test')

      expect(result).toEqual({ ok: true, data: mockData })
    })

    it('should handle response with custom headers', async () => {
      const mockData = { data: { id: 1 } }
      global.fetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockData,
      })

      await apiRequest('/test', {
        headers: { 'X-Custom-Header': 'value' },
      })

      expect(global.fetch).toHaveBeenCalledWith(
        `${API_BASE}/test`,
        expect.objectContaining({
          headers: {
            'X-Custom-Header': 'value',
          },
        })
      )
    })

    it('should handle 204 No Content response', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        status: 204,
        json: async () => {
          throw new Error('No JSON')
        },
      })

      const result = await apiRequest('/test')

      expect(result).toEqual({ ok: true, data: null })
    })
  })

  // Error cases
  describe('Error handling', () => {
    it('should handle HTTP error response', async () => {
      const errorData = {
        error: { message: 'Not found', code: 'NOT_FOUND' },
      }
      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        json: async () => errorData,
      })

      const result = await apiRequest('/test')

      expect(result).toEqual({
        ok: false,
        message: 'Not found',
        code: 'NOT_FOUND',
      })
    })

    it('should handle error with detail string', async () => {
      const errorData = { detail: 'Resource not found' }
      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        json: async () => errorData,
      })

      const result = await apiRequest('/test')

      expect(result).toEqual({
        ok: false,
        message: 'Resource not found',
        code: undefined,
      })
    })

    it('should handle error with detail object', async () => {
      const errorData = {
        detail: { message: 'Validation error', code: 'VALIDATION_ERROR' },
      }
      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: async () => errorData,
      })

      const result = await apiRequest('/test')

      expect(result).toEqual({
        ok: false,
        message: 'Validation error',
        code: 'VALIDATION_ERROR',
      })
    })

    it('should handle error with success: false', async () => {
      const errorData = { success: false, error: { message: 'Operation failed' } }
      global.fetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => errorData,
      })

      const result = await apiRequest('/test')

      expect(result).toEqual({
        ok: false,
        message: 'Operation failed',
        code: undefined,
      })
    })

    it('should handle error without message', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: async () => ({}),
      })

      const result = await apiRequest('/test')

      expect(result).toEqual({
        ok: false,
        message: 'HTTP 500',
        code: undefined,
      })
    })
  })

  // AUTH_REQUIRED handling
  describe('AUTH_REQUIRED handling', () => {
    it('should handle AUTH_REQUIRED with detail string', async () => {
      const errorData = { detail: 'AUTH_REQUIRED' }
      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: async () => errorData,
      })

      const result = await apiRequest('/test')

      expect(localStorage.getItem('authUserId')).toBeNull()
      expect(localStorage.getItem('authUsername')).toBeNull()
      expect(localStorage.getItem('authUserRole')).toBeNull()
      expect(mockLocation.href).toBe('/login')
      expect(result).toEqual({
        ok: false,
        message: 'AUTH_REQUIRED',
        code: 'AUTH_REQUIRED',
      })
    })

    it('should handle AUTH_REQUIRED with error code', async () => {
      const errorData = { error: { code: 'AUTH_REQUIRED' } }
      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: async () => errorData,
      })

      const result = await apiRequest('/test')

      expect(mockLocation.href).toBe('/login')
      expect(result).toEqual({
        ok: false,
        message: 'AUTH_REQUIRED',
        code: 'AUTH_REQUIRED',
      })
    })

    it('should handle AUTH_REQUIRED with detail.code', async () => {
      const errorData = { detail: { code: 'AUTH_REQUIRED' } }
      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: async () => errorData,
      })

      const result = await apiRequest('/test')

      expect(mockLocation.href).toBe('/login')
      expect(result).toEqual({
        ok: false,
        message: 'AUTH_REQUIRED',
        code: 'AUTH_REQUIRED',
      })
    })

    it('should clear localStorage items on AUTH_REQUIRED', async () => {
      localStorage.setItem('authUserId', '123')
      localStorage.setItem('authUsername', 'testuser')
      localStorage.setItem('authUserRole', 'user')

      const errorData = { detail: 'AUTH_REQUIRED' }
      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: async () => errorData,
      })

      await apiRequest('/test')

      expect(localStorage.getItem('authUserId')).toBeNull()
      expect(localStorage.getItem('authUsername')).toBeNull()
      expect(localStorage.getItem('authUserRole')).toBeNull()
    })
  })

  // ADMIN_ONLY handling
  describe('ADMIN_ONLY handling', () => {
    it('should handle ADMIN_ONLY with detail string', async () => {
      const errorData = { detail: 'ADMIN_ONLY' }
      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 403,
        json: async () => errorData,
      })

      const result = await apiRequest('/test')

      expect(mockLocation.href).toBe('/dashboard')
      expect(result).toEqual({
        ok: false,
        message: 'ADMIN_ONLY',
        code: 'ADMIN_ONLY',
      })
    })

    it('should handle ADMIN_ONLY with error code', async () => {
      const errorData = { error: { code: 'ADMIN_ONLY' } }
      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 403,
        json: async () => errorData,
      })

      const result = await apiRequest('/test')

      expect(mockLocation.href).toBe('/dashboard')
      expect(result).toEqual({
        ok: false,
        message: 'ADMIN_ONLY',
        code: 'ADMIN_ONLY',
      })
    })

    it('should handle ADMIN_ONLY with detail.code', async () => {
      const errorData = { detail: { code: 'ADMIN_ONLY' } }
      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 403,
        json: async () => errorData,
      })

      const result = await apiRequest('/test')

      expect(mockLocation.href).toBe('/dashboard')
      expect(result).toEqual({
        ok: false,
        message: 'ADMIN_ONLY',
        code: 'ADMIN_ONLY',
      })
    })
  })

  // Network errors
  describe('Network errors', () => {
    it('should handle network error', async () => {
      global.fetch.mockRejectedValueOnce(new Error('Network request failed'))

      const result = await apiRequest('/test')

      expect(result).toEqual({
        ok: false,
        message: 'Network request failed',
        code: 'NETWORK_ERROR',
      })
    })

    it('should handle network error without message', async () => {
      global.fetch.mockRejectedValueOnce(new Error())

      const result = await apiRequest('/test')

      expect(result).toEqual({
        ok: false,
        message: 'Network error',
        code: 'NETWORK_ERROR',
      })
    })

    it('should handle fetch timeout', async () => {
      global.fetch.mockRejectedValueOnce(new Error('timeout'))

      const result = await apiRequest('/test')

      expect(result).toEqual({
        ok: false,
        message: 'timeout',
        code: 'NETWORK_ERROR',
      })
    })
  })

  // Edge cases
  describe('Edge cases', () => {
    it('should handle empty response body', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => null,
      })

      const result = await apiRequest('/test')

      expect(result).toEqual({ ok: true, data: null })
    })

    it('should handle response with data property as null', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ data: null }),
      })

      const result = await apiRequest('/test')

      // When data.data is null, the nullish coalescing operator returns the original data object
      expect(result).toEqual({ ok: true, data: { data: null } })
    })

    it('should not redirect on 401 without AUTH_REQUIRED', async () => {
      const errorData = { detail: 'Invalid credentials' }
      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: async () => errorData,
      })

      const result = await apiRequest('/test')

      expect(mockLocation.href).toBe('')
      expect(result).toEqual({
        ok: false,
        message: 'Invalid credentials',
        code: undefined,
      })
    })

    it('should not redirect on 403 without ADMIN_ONLY', async () => {
      const errorData = { detail: 'Forbidden' }
      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 403,
        json: async () => errorData,
      })

      const result = await apiRequest('/test')

      expect(mockLocation.href).toBe('')
      expect(result).toEqual({
        ok: false,
        message: 'Forbidden',
        code: undefined,
      })
    })
  })
})

