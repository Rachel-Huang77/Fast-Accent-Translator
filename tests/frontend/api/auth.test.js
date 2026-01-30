// tests/frontend/api/auth.test.js
import { describe, it, expect, vi, beforeEach } from 'vitest'
import * as authAPI from '@src/api/auth'
import { apiRequest } from '@src/config/api.js'

// Mock apiRequest
vi.mock('@src/config/api.js', () => ({
  apiRequest: vi.fn(),
}))

describe('auth API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
  })

  describe('login', () => {
    it('should login successfully with username and password', async () => {
      const mockResponse = {
        ok: true,
        data: {
          user: { id: '1', username: 'testuser', email: 'test@example.com', role: 'user' },
          accessToken: 'token123',
        },
      }
      apiRequest.mockResolvedValueOnce(mockResponse)

      const result = await authAPI.login({ username: 'testuser', password: 'password123' })

      expect(apiRequest).toHaveBeenCalledWith('/auth/login', {
        method: 'POST',
        body: { username: 'testuser', password: 'password123' },
      })
      expect(result).toEqual({
        ok: true,
        token: 'token123',
        user: {
          id: '1',
          username: 'testuser',
          email: 'test@example.com',
          role: 'user',
        },
      })
    })

    it('should handle login failure', async () => {
      const mockResponse = {
        ok: false,
        message: 'Invalid credentials',
      }
      apiRequest.mockResolvedValueOnce(mockResponse)

      const result = await authAPI.login({ username: 'testuser', password: 'wrong' })

      expect(result).toEqual({
        ok: false,
        message: 'Invalid credentials',
      })
    })

    it('should handle user without email', async () => {
      const mockResponse = {
        ok: true,
        data: {
          user: { id: '1', username: 'testuser', role: 'user' },
          accessToken: 'token123',
        },
      }
      apiRequest.mockResolvedValueOnce(mockResponse)

      const result = await authAPI.login({ username: 'testuser', password: 'password123' })

      expect(result.user.email).toBe('')
    })
  })

  describe('logout', () => {
    it('should logout successfully', async () => {
      const mockResponse = {
        ok: true,
        message: 'Logged out successfully',
      }
      apiRequest.mockResolvedValueOnce(mockResponse)

      const result = await authAPI.logout()

      expect(apiRequest).toHaveBeenCalledWith('/auth/logout', {
        method: 'POST',
      })
      expect(result).toEqual(mockResponse)
    })

    it('should return response even if logout fails', async () => {
      const mockResponse = {
        ok: false,
        message: 'Logout failed',
      }
      apiRequest.mockResolvedValueOnce(mockResponse)

      const result = await authAPI.logout()

      expect(result).toEqual(mockResponse)
    })
  })

  describe('register', () => {
    it('should register successfully', async () => {
      const mockResponse = {
        ok: true,
        data: {
          id: '1',
          username: 'newuser',
          email: 'newuser@example.com',
        },
      }
      apiRequest.mockResolvedValueOnce(mockResponse)

      const result = await authAPI.register({
        username: 'newuser',
        email: 'newuser@example.com',
        password: 'Password123!',
      })

      expect(apiRequest).toHaveBeenCalledWith('/auth/register', {
        method: 'POST',
        body: {
          username: 'newuser',
          email: 'newuser@example.com',
          password: 'Password123!',
        },
      })
      expect(result).toEqual({
        ok: true,
        message: 'Registration successful',
        user: {
          id: '1',
          username: 'newuser',
          email: 'newuser@example.com',
        },
      })
    })

    it('should handle registration failure', async () => {
      const mockResponse = {
        ok: false,
        message: 'Username already exists',
      }
      apiRequest.mockResolvedValueOnce(mockResponse)

      const result = await authAPI.register({
        username: 'existinguser',
        email: 'existing@example.com',
        password: 'Password123!',
      })

      expect(result).toEqual({
        ok: false,
        message: 'Username already exists',
      })
    })

    it('should handle user without email in response', async () => {
      const mockResponse = {
        ok: true,
        data: {
          id: '1',
          username: 'newuser',
        },
      }
      apiRequest.mockResolvedValueOnce(mockResponse)

      const result = await authAPI.register({
        username: 'newuser',
        email: 'newuser@example.com',
        password: 'Password123!',
      })

      expect(result.user.email).toBe('')
    })
  })

  describe('checkUserForReset', () => {
    it('should check user for reset successfully', async () => {
      const mockResponse = {
        ok: true,
        data: {
          userId: '123',
        },
      }
      apiRequest.mockResolvedValueOnce(mockResponse)

      const result = await authAPI.checkUserForReset({
        username: 'testuser',
        email: 'test@example.com',
      })

      expect(apiRequest).toHaveBeenCalledWith('/auth/check-reset', {
        method: 'POST',
        body: {
          username: 'testuser',
          email: 'test@example.com',
        },
      })
      expect(result).toEqual({
        ok: true,
        userId: '123',
      })
    })

    it('should handle check failure', async () => {
      const mockResponse = {
        ok: false,
        message: 'User not found',
      }
      apiRequest.mockResolvedValueOnce(mockResponse)

      const result = await authAPI.checkUserForReset({
        username: 'nonexistent',
        email: 'nonexistent@example.com',
      })

      expect(result).toEqual({
        ok: false,
        message: 'User not found',
      })
    })
  })

  describe('resetPassword', () => {
    it('should reset password successfully', async () => {
      const mockResponse = {
        ok: true,
        message: 'Password updated successfully',
      }
      apiRequest.mockResolvedValueOnce(mockResponse)

      const result = await authAPI.resetPassword({
        userId: '123',
        newPassword: 'NewPassword123!',
      })

      expect(apiRequest).toHaveBeenCalledWith('/auth/reset-password', {
        method: 'POST',
        body: {
          userId: '123',
          newPassword: 'NewPassword123!',
        },
      })
      expect(result).toEqual({
        ok: true,
        message: 'Password updated successfully',
      })
    })

    it('should handle reset password failure', async () => {
      const mockResponse = {
        ok: false,
        message: 'Failed to update password',
      }
      apiRequest.mockResolvedValueOnce(mockResponse)

      const result = await authAPI.resetPassword({
        userId: '123',
        newPassword: 'NewPassword123!',
      })

      expect(result).toEqual({
        ok: false,
        message: 'Failed to update password',
      })
    })
  })

  describe('changePassword', () => {
    it('should change password successfully', async () => {
      const mockResponse = {
        ok: true,
        message: 'Password changed successfully',
      }
      apiRequest.mockResolvedValueOnce(mockResponse)

      const result = await authAPI.changePassword({
        newPassword: 'NewPassword123!',
      })

      expect(apiRequest).toHaveBeenCalledWith('/auth/change-password', {
        method: 'POST',
        body: {
          newPassword: 'NewPassword123!',
        },
      })
      expect(result).toEqual({
        ok: true,
      })
    })

    it('should handle change password failure', async () => {
      const mockResponse = {
        ok: false,
        message: 'Current password is incorrect',
      }
      apiRequest.mockResolvedValueOnce(mockResponse)

      const result = await authAPI.changePassword({
        newPassword: 'NewPassword123!',
      })

      expect(result).toEqual({
        ok: false,
        message: 'Current password is incorrect',
      })
    })
  })
})

