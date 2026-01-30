// src/pages/Admin/__tests__/AdminUserManagement.test.jsx
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import AdminUserManagement from '@src/pages/Admin/AdminUserManagement'

// Mock admin API
vi.mock('@src/api/admin', () => ({
  listUsers: vi.fn(),
  updateUser: vi.fn(),
  deleteUser: vi.fn(),
  resetUserPassword: vi.fn(),
}))

// Mock validators
vi.mock('@src/utils/validators', () => ({
  validatePasswordComplexity: vi.fn(),
  validateEmailFormat: vi.fn(),
}))

// Import after mocking
import * as adminAPI from '@src/api/admin'
import * as validators from '@src/utils/validators'

describe('AdminUserManagement', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    validators.validateEmailFormat.mockReturnValue(null)
    validators.validatePasswordComplexity.mockReturnValue(null)
  })

  // Happy cases - rendering
  it('should render user management page', () => {
    adminAPI.listUsers.mockResolvedValue({
      ok: true,
      data: { items: [], total: 0 },
    })

    render(<AdminUserManagement />)

    expect(screen.getByText('User Management')).toBeInTheDocument()
    expect(screen.getByPlaceholderText(/Search users/i)).toBeInTheDocument()
  })

  it('should display users list', async () => {
    const mockUsers = [
      {
        id: '1',
        username: 'user1',
        email: 'user1@example.com',
        role: 'user',
        created_at: '2024-01-01T00:00:00Z',
      },
      {
        id: '2',
        username: 'admin1',
        email: 'admin1@example.com',
        role: 'admin',
        created_at: '2024-01-02T00:00:00Z',
      },
    ]

    adminAPI.listUsers.mockResolvedValue({
      ok: true,
      data: { items: mockUsers, total: 2 },
    })

    render(<AdminUserManagement />)

    await waitFor(() => {
      expect(screen.getByText('user1')).toBeInTheDocument()
      expect(screen.getByText('admin1')).toBeInTheDocument()
    })
  })

  it('should display empty state when no users', async () => {
    adminAPI.listUsers.mockResolvedValue({
      ok: true,
      data: { items: [], total: 0 },
    })

    render(<AdminUserManagement />)

    await waitFor(() => {
      expect(screen.getByText('No users found.')).toBeInTheDocument()
    })
  })

  // Search functionality
  it('should search users when typing in search box', async () => {
    const user = userEvent.setup()
    adminAPI.listUsers.mockResolvedValue({
      ok: true,
      data: { items: [], total: 0 },
    })

    render(<AdminUserManagement />)

    const searchInput = screen.getByPlaceholderText(/Search users/i)
    await user.type(searchInput, 'test')

    await waitFor(() => {
      expect(adminAPI.listUsers).toHaveBeenCalledWith(
        expect.objectContaining({ q: 'test' })
      )
    })
  })

  // Edit user functionality
  it('should open edit modal when edit button is clicked', async () => {
    const user = userEvent.setup()
    const mockUser = {
      id: '1',
      username: 'testuser',
      email: 'test@example.com',
      role: 'user',
      created_at: '2024-01-01T00:00:00Z',
    }

    adminAPI.listUsers.mockResolvedValue({
      ok: true,
      data: { items: [mockUser], total: 1 },
    })

    render(<AdminUserManagement />)

    await waitFor(() => {
      expect(screen.getByText('testuser')).toBeInTheDocument()
    })

    const editButton = screen.getByRole('button', { name: /edit/i })
    await user.click(editButton)

    await waitFor(() => {
      expect(screen.getByText('Edit User')).toBeInTheDocument()
      expect(screen.getByDisplayValue('testuser')).toBeInTheDocument()
      expect(screen.getByDisplayValue('test@example.com')).toBeInTheDocument()
    })
  })

  it('should update user when edit form is submitted', async () => {
    const user = userEvent.setup()
    const mockUser = {
      id: '1',
      username: 'testuser',
      email: 'test@example.com',
      role: 'user',
      created_at: '2024-01-01T00:00:00Z',
    }

    adminAPI.listUsers.mockResolvedValue({
      ok: true,
      data: { items: [mockUser], total: 1 },
    })
    adminAPI.updateUser.mockResolvedValue({
      ok: true,
      data: { user: { ...mockUser, username: 'updateduser' } },
    })

    render(<AdminUserManagement />)

    await waitFor(() => {
      expect(screen.getByText('testuser')).toBeInTheDocument()
    })

    const editButton = screen.getByRole('button', { name: /edit/i })
    await user.click(editButton)

    await waitFor(() => {
      expect(screen.getByText('Edit User')).toBeInTheDocument()
    })

    const usernameInput = screen.getByDisplayValue('testuser')
    await user.clear(usernameInput)
    await user.type(usernameInput, 'updateduser')

    const submitButton = screen.getByRole('button', { name: /submit/i })
    await user.click(submitButton)

    await waitFor(() => {
      expect(adminAPI.updateUser).toHaveBeenCalledWith('1', {
        username: 'updateduser',
        email: 'test@example.com',
      })
    })
  })

  it('should show error when username is empty in edit form', async () => {
    const user = userEvent.setup()
    const mockUser = {
      id: '1',
      username: 'testuser',
      email: 'test@example.com',
      role: 'user',
      created_at: '2024-01-01T00:00:00Z',
    }

    adminAPI.listUsers.mockResolvedValue({
      ok: true,
      data: { items: [mockUser], total: 1 },
    })

    render(<AdminUserManagement />)

    await waitFor(() => {
      expect(screen.getByText('testuser')).toBeInTheDocument()
    })

    const editButton = screen.getByRole('button', { name: /edit/i })
    await user.click(editButton)

    await waitFor(() => {
      expect(screen.getByText('Edit User')).toBeInTheDocument()
    })

    const usernameInput = screen.getByDisplayValue('testuser')
    await user.clear(usernameInput)

    const submitButton = screen.getByRole('button', { name: /submit/i })
    await user.click(submitButton)

    await waitFor(() => {
      expect(screen.getByText('Username cannot be empty.')).toBeInTheDocument()
    })
  })

  // Delete user functionality
  it('should open delete confirmation modal when delete button is clicked', async () => {
    const user = userEvent.setup()
    const mockUser = {
      id: '1',
      username: 'testuser',
      email: 'test@example.com',
      role: 'user',
      created_at: '2024-01-01T00:00:00Z',
    }

    adminAPI.listUsers.mockResolvedValue({
      ok: true,
      data: { items: [mockUser], total: 1 },
    })

    render(<AdminUserManagement />)

    await waitFor(() => {
      expect(screen.getByText('testuser')).toBeInTheDocument()
    })

    const deleteButton = screen.getByRole('button', { name: /delete/i })
    await user.click(deleteButton)

    await waitFor(() => {
      // Use getByRole for heading to avoid multiple matches
      expect(screen.getByRole('heading', { name: /confirm delete/i })).toBeInTheDocument()
      expect(screen.getByText(/Are you sure you want to delete user/i)).toBeInTheDocument()
      // testuser appears in both table and modal, use getAllByText and check at least one exists
      const testuserElements = screen.getAllByText('testuser')
      expect(testuserElements.length).toBeGreaterThan(0)
    })
  })

  it('should delete user when confirmed', async () => {
    const user = userEvent.setup()
    const mockUser = {
      id: '1',
      username: 'testuser',
      email: 'test@example.com',
      role: 'user',
      created_at: '2024-01-01T00:00:00Z',
    }

    adminAPI.listUsers.mockResolvedValue({
      ok: true,
      data: { items: [mockUser], total: 1 },
    })
    adminAPI.deleteUser.mockResolvedValue({ ok: true })

    render(<AdminUserManagement />)

    await waitFor(() => {
      expect(screen.getByText('testuser')).toBeInTheDocument()
    })

    const deleteButton = screen.getByRole('button', { name: /delete/i })
    await user.click(deleteButton)

    await waitFor(() => {
      // Use getByRole for heading to avoid multiple matches
      expect(screen.getByRole('heading', { name: /confirm delete/i })).toBeInTheDocument()
    })

    const confirmButton = screen.getByRole('button', { name: /confirm delete/i })
    await user.click(confirmButton)

    await waitFor(() => {
      expect(adminAPI.deleteUser).toHaveBeenCalledWith('1')
      expect(screen.getByText('User deleted successfully.')).toBeInTheDocument()
    })
  })

  // Reset password functionality
  it('should open reset password modal when reset password button is clicked', async () => {
    const user = userEvent.setup()
    const mockUser = {
      id: '1',
      username: 'testuser',
      email: 'test@example.com',
      role: 'user',
      created_at: '2024-01-01T00:00:00Z',
    }

    adminAPI.listUsers.mockResolvedValue({
      ok: true,
      data: { items: [mockUser], total: 1 },
    })

    render(<AdminUserManagement />)

    await waitFor(() => {
      expect(screen.getByText('testuser')).toBeInTheDocument()
    })

    const resetButton = screen.getByRole('button', { name: /reset password/i })
    await user.click(resetButton)

    await waitFor(() => {
      // Use getByRole for heading to avoid multiple matches
      expect(screen.getByRole('heading', { name: /reset password/i })).toBeInTheDocument()
      expect(screen.getByText(/Set new password for user/i)).toBeInTheDocument()
    })
  })

  it('should reset password when form is submitted', async () => {
    const user = userEvent.setup()
    const mockUser = {
      id: '1',
      username: 'testuser',
      email: 'test@example.com',
      role: 'user',
      created_at: '2024-01-01T00:00:00Z',
    }

    adminAPI.listUsers.mockResolvedValue({
      ok: true,
      data: { items: [mockUser], total: 1 },
    })
    adminAPI.resetUserPassword.mockResolvedValue({ ok: true })

    render(<AdminUserManagement />)

    await waitFor(() => {
      expect(screen.getByText('testuser')).toBeInTheDocument()
    })

    const resetButton = screen.getByRole('button', { name: /reset password/i })
    await user.click(resetButton)

    await waitFor(() => {
      // Use getByRole for heading to avoid multiple matches
      expect(screen.getByRole('heading', { name: /reset password/i })).toBeInTheDocument()
    })

    const passwordInput = screen.getByPlaceholderText(/Enter new password/i)
    await user.type(passwordInput, 'NewPassword123!')

    const confirmButton = screen.getByRole('button', { name: /confirm reset/i })
    await user.click(confirmButton)

    await waitFor(() => {
      expect(adminAPI.resetUserPassword).toHaveBeenCalledWith('1', 'NewPassword123!')
    })
  })

  it('should show error when password complexity is invalid', async () => {
    const user = userEvent.setup()
    const mockUser = {
      id: '1',
      username: 'testuser',
      email: 'test@example.com',
      role: 'user',
      created_at: '2024-01-01T00:00:00Z',
    }

    adminAPI.listUsers.mockResolvedValue({
      ok: true,
      data: { items: [mockUser], total: 1 },
    })
    validators.validatePasswordComplexity.mockReturnValue('Password does not meet complexity requirements')

    render(<AdminUserManagement />)

    await waitFor(() => {
      expect(screen.getByText('testuser')).toBeInTheDocument()
    })

    const resetButton = screen.getByRole('button', { name: /reset password/i })
    await user.click(resetButton)

    await waitFor(() => {
      // Use getByRole for heading to avoid multiple matches
      expect(screen.getByRole('heading', { name: /reset password/i })).toBeInTheDocument()
    })

    const passwordInput = screen.getByPlaceholderText(/Enter new password/i)
    await user.type(passwordInput, 'weak')

    const confirmButton = screen.getByRole('button', { name: /confirm reset/i })
    await user.click(confirmButton)

    await waitFor(() => {
      expect(screen.getByText('Password does not meet complexity requirements')).toBeInTheDocument()
    })

    expect(adminAPI.resetUserPassword).not.toHaveBeenCalled()
  })

  // Pagination
  it('should handle pagination', async () => {
    const user = userEvent.setup()
    adminAPI.listUsers.mockResolvedValue({
      ok: true,
      data: { items: [], total: 50 },
    })

    render(<AdminUserManagement />)

    await waitFor(() => {
      expect(screen.getByText(/Page 1/i)).toBeInTheDocument()
    })

    const nextButton = screen.getByRole('button', { name: /next/i })
    await user.click(nextButton)

    await waitFor(() => {
      expect(adminAPI.listUsers).toHaveBeenCalledWith(
        expect.objectContaining({ offset: 20 })
      )
    })
  })

  // Error handling
  it('should display error message when loading users fails', async () => {
    adminAPI.listUsers.mockResolvedValue({
      ok: false,
      message: 'Failed to load users',
    })

    render(<AdminUserManagement />)

    await waitFor(() => {
      expect(screen.getByText('Failed to load users')).toBeInTheDocument()
    })
  })

  it('should display error message when update fails', async () => {
    const user = userEvent.setup()
    const mockUser = {
      id: '1',
      username: 'testuser',
      email: 'test@example.com',
      role: 'user',
      created_at: '2024-01-01T00:00:00Z',
    }

    adminAPI.listUsers.mockResolvedValue({
      ok: true,
      data: { items: [mockUser], total: 1 },
    })
    adminAPI.updateUser.mockResolvedValue({
      ok: false,
      message: 'Update failed',
    })

    render(<AdminUserManagement />)

    await waitFor(() => {
      expect(screen.getByText('testuser')).toBeInTheDocument()
    })

    const editButton = screen.getByRole('button', { name: /edit/i })
    await user.click(editButton)

    await waitFor(() => {
      expect(screen.getByText('Edit User')).toBeInTheDocument()
    })

    const submitButton = screen.getByRole('button', { name: /submit/i })
    await user.click(submitButton)

    await waitFor(() => {
      expect(screen.getByText('Update failed')).toBeInTheDocument()
    })
  })
})

