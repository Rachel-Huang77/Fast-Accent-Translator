// src/pages/ForgotPassword/__tests__/ForgotPasswordPage.test.jsx
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter } from 'react-router-dom'

// Mock the auth API BEFORE importing ForgotPasswordPage
vi.mock('@src/api/auth', () => ({
  login: vi.fn(),
  logout: vi.fn(),
  register: vi.fn(),
  checkUserForReset: vi.fn(),
  resetPassword: vi.fn(),
  changePassword: vi.fn(),
}))

// Mock validators
vi.mock('@src/utils/validators', () => ({
  validatePasswordComplexity: vi.fn(),
  validateEmailFormat: vi.fn(),
}))

// Import after mocking
import ForgotPasswordPage from '@src/pages/ForgotPassword/ForgotPasswordPage'
import * as authAPI from '@src/api/auth'
import * as validators from '@src/utils/validators'

// Mock useNavigate
const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

// Helper function to render component with router
const renderWithRouter = (component) => {
  return render(<BrowserRouter>{component}</BrowserRouter>)
}

describe('ForgotPasswordPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockNavigate.mockClear()
    localStorage.clear()
    
    // Reset mock implementations
    if (authAPI.checkUserForReset && typeof authAPI.checkUserForReset.mockClear === 'function') {
      authAPI.checkUserForReset.mockClear()
      authAPI.checkUserForReset.mockReset()
    }
    if (authAPI.resetPassword && typeof authAPI.resetPassword.mockClear === 'function') {
      authAPI.resetPassword.mockClear()
      authAPI.resetPassword.mockReset()
    }
    
    // Default validators return null (no error)
    validators.validateEmailFormat.mockReturnValue(null)
    validators.validatePasswordComplexity.mockReturnValue(null)
  })

  // Happy cases - rendering
  it('should render forgot password form with all required elements', () => {
    renderWithRouter(<ForgotPasswordPage />)
    
    expect(screen.getByText(/Reset your password/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/username/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /confirm/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument()
  })

  it('should not show password modal initially', () => {
    renderWithRouter(<ForgotPasswordPage />)
    
    expect(screen.queryByText(/Set a new password/i)).not.toBeInTheDocument()
  })

  // Happy cases - user interactions
  it('should update username input when user types', async () => {
    const user = userEvent.setup()
    renderWithRouter(<ForgotPasswordPage />)
    
    const usernameInput = screen.getByLabelText(/username/i)
    await user.type(usernameInput, 'testuser')
    
    expect(usernameInput).toHaveValue('testuser')
  })

  it('should update email input when user types', async () => {
    const user = userEvent.setup()
    renderWithRouter(<ForgotPasswordPage />)
    
    const emailInput = screen.getByLabelText(/email/i)
    await user.type(emailInput, 'test@example.com')
    
    expect(emailInput).toHaveValue('test@example.com')
  })

  // Step 1: Verification
  it('should show error message when username is empty', async () => {
    const user = userEvent.setup()
    renderWithRouter(<ForgotPasswordPage />)
    
    await user.type(screen.getByLabelText(/email/i), 'test@example.com')
    await user.click(screen.getByRole('button', { name: /confirm/i }))
    
    await waitFor(() => {
      expect(screen.getByText('Please enter both username and email.')).toBeInTheDocument()
    })
    
    expect(authAPI.checkUserForReset).not.toHaveBeenCalled()
  })

  it('should show error message when email is empty', async () => {
    const user = userEvent.setup()
    renderWithRouter(<ForgotPasswordPage />)
    
    await user.type(screen.getByLabelText(/username/i), 'testuser')
    await user.click(screen.getByRole('button', { name: /confirm/i }))
    
    await waitFor(() => {
      expect(screen.getByText('Please enter both username and email.')).toBeInTheDocument()
    })
    
    expect(authAPI.checkUserForReset).not.toHaveBeenCalled()
  })

  it('should open password modal when verification succeeds', async () => {
    const user = userEvent.setup()
    authAPI.checkUserForReset.mockResolvedValue({
      ok: true,
      userId: '123'
    })
    
    renderWithRouter(<ForgotPasswordPage />)
    
    await user.type(screen.getByLabelText(/username/i), 'testuser')
    await user.type(screen.getByLabelText(/email/i), 'test@example.com')
    await user.click(screen.getByRole('button', { name: /confirm/i }))
    
    await waitFor(() => {
      expect(screen.getByText(/Set a new password/i)).toBeInTheDocument()
    })
    
    expect(authAPI.checkUserForReset).toHaveBeenCalledWith({
      username: 'testuser',
      email: 'test@example.com'
    })
  })

  it('should show error message when verification fails', async () => {
    const user = userEvent.setup()
    authAPI.checkUserForReset.mockResolvedValue({
      ok: false,
      message: 'User not found'
    })
    
    renderWithRouter(<ForgotPasswordPage />)
    
    await user.type(screen.getByLabelText(/username/i), 'testuser')
    await user.type(screen.getByLabelText(/email/i), 'test@example.com')
    await user.click(screen.getByRole('button', { name: /confirm/i }))
    
    await waitFor(() => {
      expect(screen.getByText('User not found')).toBeInTheDocument()
    })
    
    expect(screen.queryByText(/Set a new password/i)).not.toBeInTheDocument()
  })

  it('should trim username and email before verification', async () => {
    const user = userEvent.setup()
    authAPI.checkUserForReset.mockResolvedValue({
      ok: true,
      userId: '123'
    })
    
    renderWithRouter(<ForgotPasswordPage />)
    
    await user.type(screen.getByLabelText(/username/i), '  testuser  ')
    await user.type(screen.getByLabelText(/email/i), '  test@example.com  ')
    await user.click(screen.getByRole('button', { name: /confirm/i }))
    
    await waitFor(() => {
      expect(authAPI.checkUserForReset).toHaveBeenCalledWith({
        username: 'testuser',
        email: 'test@example.com'
      })
    })
  })

  // Step 2: Password Reset Modal
  it('should close modal when cancel button is clicked', async () => {
    const user = userEvent.setup()
    authAPI.checkUserForReset.mockResolvedValue({
      ok: true,
      userId: '123'
    })
    
    renderWithRouter(<ForgotPasswordPage />)
    
    // Open modal
    await user.type(screen.getByLabelText(/username/i), 'testuser')
    await user.type(screen.getByLabelText(/email/i), 'test@example.com')
    await user.click(screen.getByRole('button', { name: /confirm/i }))
    
    await waitFor(() => {
      expect(screen.getByText(/Set a new password/i)).toBeInTheDocument()
    })
    
    // Close modal
    const cancelButtons = screen.getAllByRole('button', { name: /cancel/i })
    await user.click(cancelButtons[cancelButtons.length - 1]) // Click modal cancel button
    
    await waitFor(() => {
      expect(screen.queryByText(/Set a new password/i)).not.toBeInTheDocument()
    })
  })

  it('should update password input in modal when user types', async () => {
    const user = userEvent.setup()
    authAPI.checkUserForReset.mockResolvedValue({
      ok: true,
      userId: '123'
    })
    
    renderWithRouter(<ForgotPasswordPage />)
    
    // Open modal
    await user.type(screen.getByLabelText(/username/i), 'testuser')
    await user.type(screen.getByLabelText(/email/i), 'test@example.com')
    await user.click(screen.getByRole('button', { name: /confirm/i }))
    
    await waitFor(() => {
      expect(screen.getByText(/Set a new password/i)).toBeInTheDocument()
    })
    
    const passwordInput = screen.getByPlaceholderText(/Enter new password/i)
    await user.type(passwordInput, 'NewPassword123!')
    
    expect(passwordInput).toHaveValue('NewPassword123!')
  })

  it('should toggle password visibility in modal', async () => {
    const user = userEvent.setup()
    authAPI.checkUserForReset.mockResolvedValue({
      ok: true,
      userId: '123'
    })
    
    renderWithRouter(<ForgotPasswordPage />)
    
    // Open modal
    await user.type(screen.getByLabelText(/username/i), 'testuser')
    await user.type(screen.getByLabelText(/email/i), 'test@example.com')
    await user.click(screen.getByRole('button', { name: /confirm/i }))
    
    await waitFor(() => {
      expect(screen.getByText(/Set a new password/i)).toBeInTheDocument()
    })
    
    const passwordInput = screen.getByPlaceholderText(/Enter new password/i)
    const eyeButton = screen.getAllByLabelText(/show password/i).find(btn => 
      btn.closest('[class*="modal"]') !== null
    )
    
    expect(passwordInput).toHaveAttribute('type', 'password')
    
    await user.click(eyeButton)
    expect(passwordInput).toHaveAttribute('type', 'text')
    
    await user.click(screen.getAllByLabelText(/hide password/i).find(btn => 
      btn.closest('[class*="modal"]') !== null
    ))
    expect(passwordInput).toHaveAttribute('type', 'password')
  })

  it('should show error message when password is empty in modal', async () => {
    const user = userEvent.setup()
    authAPI.checkUserForReset.mockResolvedValue({
      ok: true,
      userId: '123'
    })
    
    renderWithRouter(<ForgotPasswordPage />)
    
    // Open modal
    await user.type(screen.getByLabelText(/username/i), 'testuser')
    await user.type(screen.getByLabelText(/email/i), 'test@example.com')
    await user.click(screen.getByRole('button', { name: /confirm/i }))
    
    await waitFor(() => {
      expect(screen.getByText(/Set a new password/i)).toBeInTheDocument()
    })
    
    // Try to confirm without password
    const confirmButtons = screen.getAllByRole('button', { name: /confirm/i })
    await user.click(confirmButtons[confirmButtons.length - 1]) // Click modal confirm button
    
    await waitFor(() => {
      expect(screen.getByText('Please enter a new password.')).toBeInTheDocument()
    })
    
    expect(authAPI.resetPassword).not.toHaveBeenCalled()
  })

  it('should show error message when password complexity is invalid in modal', async () => {
    const user = userEvent.setup()
    validators.validatePasswordComplexity.mockReturnValue('Password does not meet complexity requirements')
    authAPI.checkUserForReset.mockResolvedValue({
      ok: true,
      userId: '123'
    })
    
    renderWithRouter(<ForgotPasswordPage />)
    
    // Open modal
    await user.type(screen.getByLabelText(/username/i), 'testuser')
    await user.type(screen.getByLabelText(/email/i), 'test@example.com')
    await user.click(screen.getByRole('button', { name: /confirm/i }))
    
    await waitFor(() => {
      expect(screen.getByText(/Set a new password/i)).toBeInTheDocument()
    })
    
    const passwordInput = screen.getByPlaceholderText(/Enter new password/i)
    await user.type(passwordInput, 'weak')
    
    const confirmButtons = screen.getAllByRole('button', { name: /confirm/i })
    await user.click(confirmButtons[confirmButtons.length - 1])
    
    await waitFor(() => {
      expect(screen.getByText('Password does not meet complexity requirements')).toBeInTheDocument()
    })
    
    expect(authAPI.resetPassword).not.toHaveBeenCalled()
  })

  it('should navigate to login page after successful password reset', async () => {
    const user = userEvent.setup()
    authAPI.checkUserForReset.mockResolvedValue({
      ok: true,
      userId: '123'
    })
    authAPI.resetPassword.mockResolvedValue({
      ok: true,
      message: 'Password updated successfully'
    })
    
    renderWithRouter(<ForgotPasswordPage />)
    
    // Open modal
    await user.type(screen.getByLabelText(/username/i), 'testuser')
    await user.type(screen.getByLabelText(/email/i), 'test@example.com')
    await user.click(screen.getByRole('button', { name: /confirm/i }))
    
    await waitFor(() => {
      expect(screen.getByText(/Set a new password/i)).toBeInTheDocument()
    })
    
    // Set new password
    const passwordInput = screen.getByPlaceholderText(/Enter new password/i)
    await user.type(passwordInput, 'NewPassword123!')
    
    const confirmButtons = screen.getAllByRole('button', { name: /confirm/i })
    await user.click(confirmButtons[confirmButtons.length - 1])
    
    await waitFor(() => {
      expect(screen.getByText('Password updated successfully')).toBeInTheDocument()
    })
    
    // Wait for navigation timeout (800ms)
    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/login', { replace: true })
    }, { timeout: 2000 })
  })

  it('should show error message when password reset fails', async () => {
    const user = userEvent.setup()
    authAPI.checkUserForReset.mockResolvedValue({
      ok: true,
      userId: '123'
    })
    authAPI.resetPassword.mockResolvedValue({
      ok: false,
      message: 'Failed to update password'
    })
    
    renderWithRouter(<ForgotPasswordPage />)
    
    // Open modal
    await user.type(screen.getByLabelText(/username/i), 'testuser')
    await user.type(screen.getByLabelText(/email/i), 'test@example.com')
    await user.click(screen.getByRole('button', { name: /confirm/i }))
    
    await waitFor(() => {
      expect(screen.getByText(/Set a new password/i)).toBeInTheDocument()
    })
    
    // Set new password
    const passwordInput = screen.getByPlaceholderText(/Enter new password/i)
    await user.type(passwordInput, 'NewPassword123!')
    
    const confirmButtons = screen.getAllByRole('button', { name: /confirm/i })
    await user.click(confirmButtons[confirmButtons.length - 1])
    
    await waitFor(() => {
      expect(screen.getByText('Failed to update password')).toBeInTheDocument()
    })
    
    expect(mockNavigate).not.toHaveBeenCalled()
  })

  it('should show loading state during verification', async () => {
    const user = userEvent.setup()
    authAPI.checkUserForReset.mockImplementation(() => new Promise(resolve => setTimeout(() => resolve({
      ok: true,
      userId: '123'
    }), 100)))
    
    renderWithRouter(<ForgotPasswordPage />)
    
    await user.type(screen.getByLabelText(/username/i), 'testuser')
    await user.type(screen.getByLabelText(/email/i), 'test@example.com')
    await user.click(screen.getByRole('button', { name: /confirm/i }))
    
    expect(screen.getByRole('button', { name: /checking/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /checking/i })).toBeDisabled()
  })

  it('should show loading state during password reset', async () => {
    const user = userEvent.setup()
    authAPI.checkUserForReset.mockResolvedValue({
      ok: true,
      userId: '123'
    })
    authAPI.resetPassword.mockImplementation(() => new Promise(resolve => setTimeout(() => resolve({
      ok: true,
      message: 'Password updated successfully'
    }), 100)))
    
    renderWithRouter(<ForgotPasswordPage />)
    
    // Open modal
    await user.type(screen.getByLabelText(/username/i), 'testuser')
    await user.type(screen.getByLabelText(/email/i), 'test@example.com')
    await user.click(screen.getByRole('button', { name: /confirm/i }))
    
    await waitFor(() => {
      expect(screen.getByText(/Set a new password/i)).toBeInTheDocument()
    })
    
    // Set new password
    const passwordInput = screen.getByPlaceholderText(/Enter new password/i)
    await user.type(passwordInput, 'NewPassword123!')
    
    const confirmButtons = screen.getAllByRole('button', { name: /confirm/i })
    await user.click(confirmButtons[confirmButtons.length - 1])
    
    expect(screen.getByRole('button', { name: /saving/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /saving/i })).toBeDisabled()
  })

  // User interactions - navigation
  it('should navigate to login page when cancel button is clicked', async () => {
    const user = userEvent.setup()
    renderWithRouter(<ForgotPasswordPage />)
    
    await user.click(screen.getByRole('button', { name: /cancel/i }))
    expect(mockNavigate).toHaveBeenCalledWith('/login')
  })

  // Error message dismissal
  it('should dismiss error message when close button is clicked', async () => {
    const user = userEvent.setup()
    authAPI.checkUserForReset.mockResolvedValue({
      ok: false,
      message: 'Error message'
    })
    
    renderWithRouter(<ForgotPasswordPage />)
    
    await user.type(screen.getByLabelText(/username/i), 'testuser')
    await user.type(screen.getByLabelText(/email/i), 'test@example.com')
    await user.click(screen.getByRole('button', { name: /confirm/i }))
    
    await waitFor(() => {
      expect(screen.getByText('Error message')).toBeInTheDocument()
    })
    
    const closeButton = screen.getByLabelText('Close')
    await user.click(closeButton)
    
    await waitFor(() => {
      expect(screen.queryByText('Error message')).not.toBeInTheDocument()
    })
  })
})

