// src/pages/Register/__tests__/RegisterPage.test.jsx
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter } from 'react-router-dom'

// Mock the auth API BEFORE importing RegisterPage
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
import RegisterPage from '@src/pages/Register/RegisterPage'
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

describe('RegisterPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockNavigate.mockClear()
    localStorage.clear()
    
    // Reset mock implementations
    if (authAPI.register && typeof authAPI.register.mockClear === 'function') {
      authAPI.register.mockClear()
      authAPI.register.mockReset()
    }
    
    // Default validators return null (no error)
    validators.validateEmailFormat.mockReturnValue(null)
    validators.validatePasswordComplexity.mockReturnValue(null)
    
    // Note: We'll use real timers for most tests, only use fake timers when needed
  })

  // Happy cases - rendering
  it('should render registration form with all required elements', () => {
    renderWithRouter(<RegisterPage />)
    
    expect(screen.getByText(/Create your/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/username/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument()
    expect(screen.getByPlaceholderText(/enter your password/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /confirm/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument()
  })

  it('should render password hint', () => {
    renderWithRouter(<RegisterPage />)
    
    expect(screen.getByText(/Password must be at least 8 characters/i)).toBeInTheDocument()
  })

  // Happy cases - user interactions
  it('should update username input when user types', async () => {
    const user = userEvent.setup()
    renderWithRouter(<RegisterPage />)
    
    const usernameInput = screen.getByLabelText(/username/i)
    await user.type(usernameInput, 'testuser')
    
    expect(usernameInput).toHaveValue('testuser')
  })

  it('should update email input when user types', async () => {
    const user = userEvent.setup()
    renderWithRouter(<RegisterPage />)
    
    const emailInput = screen.getByLabelText(/email/i)
    await user.type(emailInput, 'test@example.com')
    
    expect(emailInput).toHaveValue('test@example.com')
  })

  it('should update password input when user types', async () => {
    const user = userEvent.setup()
    renderWithRouter(<RegisterPage />)
    
    const passwordInput = screen.getByPlaceholderText(/enter your password/i)
    await user.type(passwordInput, 'password123')
    
    expect(passwordInput).toHaveValue('password123')
  })

  it('should toggle password visibility when eye button is clicked', async () => {
    const user = userEvent.setup()
    renderWithRouter(<RegisterPage />)
    
    const passwordInput = screen.getByPlaceholderText(/enter your password/i)
    const eyeButton = screen.getByLabelText(/show password/i)
    
    expect(passwordInput).toHaveAttribute('type', 'password')
    
    await user.click(eyeButton)
    expect(passwordInput).toHaveAttribute('type', 'text')
    
    await user.click(screen.getByLabelText(/hide password/i))
    expect(passwordInput).toHaveAttribute('type', 'password')
  })

  // Sad cases - validation
  it('should show error message when username is empty', async () => {
    const user = userEvent.setup()
    renderWithRouter(<RegisterPage />)
    
    await user.type(screen.getByLabelText(/email/i), 'test@example.com')
    await user.type(screen.getByPlaceholderText(/enter your password/i), 'Password123!')
    await user.click(screen.getByRole('button', { name: /confirm/i }))
    
    await waitFor(() => {
      expect(screen.getByText('Please fill in all fields.')).toBeInTheDocument()
    })
    
    expect(authAPI.register).not.toHaveBeenCalled()
  })

  it('should show error message when email is empty', async () => {
    const user = userEvent.setup()
    renderWithRouter(<RegisterPage />)
    
    await user.type(screen.getByLabelText(/username/i), 'testuser')
    await user.type(screen.getByPlaceholderText(/enter your password/i), 'Password123!')
    await user.click(screen.getByRole('button', { name: /confirm/i }))
    
    await waitFor(() => {
      expect(screen.getByText('Please fill in all fields.')).toBeInTheDocument()
    })
    
    expect(authAPI.register).not.toHaveBeenCalled()
  })

  it('should show error message when password is empty', async () => {
    const user = userEvent.setup()
    renderWithRouter(<RegisterPage />)
    
    await user.type(screen.getByLabelText(/username/i), 'testuser')
    await user.type(screen.getByLabelText(/email/i), 'test@example.com')
    await user.click(screen.getByRole('button', { name: /confirm/i }))
    
    await waitFor(() => {
      expect(screen.getByText('Please fill in all fields.')).toBeInTheDocument()
    })
    
    expect(authAPI.register).not.toHaveBeenCalled()
  })

  it('should show error message when password complexity is invalid', async () => {
    const user = userEvent.setup()
    validators.validatePasswordComplexity.mockReturnValue('Password does not meet complexity requirements')
    
    renderWithRouter(<RegisterPage />)
    
    await user.type(screen.getByLabelText(/username/i), 'testuser')
    await user.type(screen.getByLabelText(/email/i), 'test@example.com')
    await user.type(screen.getByPlaceholderText(/enter your password/i), 'weak')
    await user.click(screen.getByRole('button', { name: /confirm/i }))
    
    await waitFor(() => {
      expect(screen.getByText('Password does not meet complexity requirements')).toBeInTheDocument()
    })
    
    expect(authAPI.register).not.toHaveBeenCalled()
  })

  it('should trim username and email before submission', async () => {
    const user = userEvent.setup()
    authAPI.register.mockResolvedValue({
      ok: true,
      message: 'Registration successful',
      user: { id: '1', username: 'testuser', email: 'test@example.com' }
    })
    
    renderWithRouter(<RegisterPage />)
    
    await user.type(screen.getByLabelText(/username/i), '  testuser  ')
    await user.type(screen.getByLabelText(/email/i), '  test@example.com  ')
    await user.type(screen.getByPlaceholderText(/enter your password/i), 'Password123!')
    await user.click(screen.getByRole('button', { name: /confirm/i }))
    
    await waitFor(() => {
      expect(authAPI.register).toHaveBeenCalledWith({
        username: 'testuser',
        email: 'test@example.com',
        password: 'Password123!'
      })
    })
  })

  // Happy cases - successful registration
  it('should navigate to login page after successful registration', async () => {
    const user = userEvent.setup()
    authAPI.register.mockResolvedValue({
      ok: true,
      message: 'Registration successful',
      user: { id: '1', username: 'testuser', email: 'test@example.com' }
    })
    
    renderWithRouter(<RegisterPage />)
    
    await user.type(screen.getByLabelText(/username/i), 'testuser')
    await user.type(screen.getByLabelText(/email/i), 'test@example.com')
    await user.type(screen.getByPlaceholderText(/enter your password/i), 'Password123!')
    await user.click(screen.getByRole('button', { name: /confirm/i }))
    
    await waitFor(() => {
      expect(screen.getByText('Registration successful')).toBeInTheDocument()
    })
    
    // Wait for navigation timeout (800ms)
    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/login', { replace: true })
    }, { timeout: 2000 })
  })

  it('should show success message after successful registration', async () => {
    const user = userEvent.setup()
    authAPI.register.mockResolvedValue({
      ok: true,
      message: 'Registration successful',
      user: { id: '1', username: 'testuser', email: 'test@example.com' }
    })
    
    renderWithRouter(<RegisterPage />)
    
    await user.type(screen.getByLabelText(/username/i), 'testuser')
    await user.type(screen.getByLabelText(/email/i), 'test@example.com')
    await user.type(screen.getByPlaceholderText(/enter your password/i), 'Password123!')
    await user.click(screen.getByRole('button', { name: /confirm/i }))
    
    await waitFor(() => {
      expect(screen.getByText('Registration successful')).toBeInTheDocument()
    })
  })

  it('should show loading state during registration', async () => {
    const user = userEvent.setup()
    authAPI.register.mockImplementation(() => new Promise(resolve => setTimeout(() => resolve({
      ok: true,
      message: 'Registration successful',
      user: { id: '1', username: 'testuser', email: 'test@example.com' }
    }), 100)))
    
    renderWithRouter(<RegisterPage />)
    
    await user.type(screen.getByLabelText(/username/i), 'testuser')
    await user.type(screen.getByLabelText(/email/i), 'test@example.com')
    await user.type(screen.getByPlaceholderText(/enter your password/i), 'Password123!')
    await user.click(screen.getByRole('button', { name: /confirm/i }))
    
    expect(screen.getByRole('button', { name: /submitting/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /submitting/i })).toBeDisabled()
  })

  // Sad cases - API errors
  it('should show error message when registration fails', async () => {
    const user = userEvent.setup()
    
    authAPI.register.mockResolvedValue({
      ok: false,
      message: 'Username already exists'
    })
    
    renderWithRouter(<RegisterPage />)
    
    await user.type(screen.getByLabelText(/username/i), 'testuser')
    await user.type(screen.getByLabelText(/email/i), 'test@example.com')
    await user.type(screen.getByPlaceholderText(/enter your password/i), 'Password123!')
    await user.click(screen.getByRole('button', { name: /confirm/i }))
    
    // Verify error message is displayed
    await waitFor(() => {
      expect(screen.getByText('Username already exists')).toBeInTheDocument()
    })
    
    // Verify user stays on the registration page (form is still visible)
    expect(screen.getByRole('button', { name: /confirm/i })).toBeInTheDocument()
    expect(screen.getByLabelText(/username/i)).toBeInTheDocument()
  })

  it('should show error message when registration throws exception', async () => {
    const user = userEvent.setup()
    authAPI.register.mockRejectedValue(new Error('Network error'))
    
    renderWithRouter(<RegisterPage />)
    
    await user.type(screen.getByLabelText(/username/i), 'testuser')
    await user.type(screen.getByLabelText(/email/i), 'test@example.com')
    await user.type(screen.getByPlaceholderText(/enter your password/i), 'Password123!')
    await user.click(screen.getByRole('button', { name: /confirm/i }))
    
    await waitFor(() => {
      expect(screen.getByText('Network error')).toBeInTheDocument()
    })
  })

  it('should handle error message object with message property', async () => {
    const user = userEvent.setup()
    authAPI.register.mockResolvedValue({
      ok: false,
      message: { message: 'Custom error message' }
    })
    
    renderWithRouter(<RegisterPage />)
    
    await user.type(screen.getByLabelText(/username/i), 'testuser')
    await user.type(screen.getByLabelText(/email/i), 'test@example.com')
    await user.type(screen.getByPlaceholderText(/enter your password/i), 'Password123!')
    await user.click(screen.getByRole('button', { name: /confirm/i }))
    
    await waitFor(() => {
      expect(screen.getByText('Custom error message')).toBeInTheDocument()
    })
  })

  // User interactions - navigation
  it('should navigate to login page when cancel button is clicked', async () => {
    const user = userEvent.setup()
    renderWithRouter(<RegisterPage />)
    
    await user.click(screen.getByRole('button', { name: /cancel/i }))
    expect(mockNavigate).toHaveBeenCalledWith('/login')
  })

  // Error message dismissal
  it('should dismiss error message when close button is clicked', async () => {
    const user = userEvent.setup()
    authAPI.register.mockResolvedValue({
      ok: false,
      message: 'Error message'
    })
    
    renderWithRouter(<RegisterPage />)
    
    await user.type(screen.getByLabelText(/username/i), 'testuser')
    await user.type(screen.getByLabelText(/email/i), 'test@example.com')
    await user.type(screen.getByPlaceholderText(/enter your password/i), 'Password123!')
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

  it('should dismiss success message when close button is clicked', async () => {
    const user = userEvent.setup()
    authAPI.register.mockResolvedValue({
      ok: true,
      message: 'Registration successful',
      user: { id: '1', username: 'testuser', email: 'test@example.com' }
    })
    
    renderWithRouter(<RegisterPage />)
    
    await user.type(screen.getByLabelText(/username/i), 'testuser')
    await user.type(screen.getByLabelText(/email/i), 'test@example.com')
    await user.type(screen.getByPlaceholderText(/enter your password/i), 'Password123!')
    await user.click(screen.getByRole('button', { name: /confirm/i }))
    
    await waitFor(() => {
      expect(screen.getByText('Registration successful')).toBeInTheDocument()
    })
    
    const closeButton = screen.getByLabelText('Close')
    await user.click(closeButton)
    
    await waitFor(() => {
      expect(screen.queryByText('Registration successful')).not.toBeInTheDocument()
    })
  })
})

