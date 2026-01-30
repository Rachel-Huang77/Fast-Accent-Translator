// tests/frontend/pages/Login/LoginPage.test.jsx
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter } from 'react-router-dom'

// Mock the auth API BEFORE importing LoginPage
vi.mock('@src/api/auth', () => ({
  login: vi.fn(),
  logout: vi.fn(),
  register: vi.fn(),
  checkUserForReset: vi.fn(),
  resetPassword: vi.fn(),
  changePassword: vi.fn(),
}))

// Import after mocking
import LoginPage from '@src/pages/Login/LoginPage'
import * as authAPI from '@src/api/auth'

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

describe('LoginPage', () => {
  beforeEach(() => {
    // Clear all mocks and localStorage FIRST
    vi.clearAllMocks()
    mockNavigate.mockClear()
    localStorage.clear()
    
    // Ensure login is a mock function and reset it
    if (authAPI.login && typeof authAPI.login.mockClear === 'function') {
      authAPI.login.mockClear()
      // Reset mock implementation to prevent any default behavior
      authAPI.login.mockReset()
    }
  })

  // Happy cases - rendering
  it('should render login form with all required elements', () => {
    renderWithRouter(<LoginPage />)
    
    expect(screen.getByText(/Welcome to/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/username/i)).toBeInTheDocument()
    expect(screen.getByPlaceholderText(/enter your password/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument()
  })

  it('should render register and forgot password links', () => {
    renderWithRouter(<LoginPage />)
    
    expect(screen.getByText('Register')).toBeInTheDocument()
    expect(screen.getByText('Forget password?')).toBeInTheDocument()
  })

  // Happy cases - user interactions
  it('should update username input when user types', async () => {
    const user = userEvent.setup()
    renderWithRouter(<LoginPage />)
    
    const usernameInput = screen.getByLabelText(/username/i)
    await user.type(usernameInput, 'testuser')
    
    expect(usernameInput).toHaveValue('testuser')
  })

  it('should update password input when user types', async () => {
    const user = userEvent.setup()
    renderWithRouter(<LoginPage />)
    
    const passwordInput = screen.getByPlaceholderText(/enter your password/i)
    await user.type(passwordInput, 'testpass123')
    
    expect(passwordInput).toHaveValue('testpass123')
  })

  it('should toggle password visibility when eye button is clicked', async () => {
    const user = userEvent.setup()
    renderWithRouter(<LoginPage />)
    
    const passwordInput = screen.getByPlaceholderText(/enter your password/i)
    const eyeButton = screen.getByLabelText(/show password/i)
    
    // Initially password type
    expect(passwordInput).toHaveAttribute('type', 'password')
    
    // Click to show password
    await user.click(eyeButton)
    expect(passwordInput).toHaveAttribute('type', 'text')
    expect(screen.getByLabelText(/hide password/i)).toBeInTheDocument()
    
    // Click to hide password
    await user.click(screen.getByLabelText(/hide password/i))
    expect(passwordInput).toHaveAttribute('type', 'password')
  })

  // Happy cases - successful login
  it('should navigate to dashboard after successful login for regular user', async () => {
    const user = userEvent.setup()
    authAPI.login.mockResolvedValue({
      ok: true,
      token: 'test-token',
      user: { id: '1', username: 'testuser', email: 'test@example.com', role: 'user' }
    })

    renderWithRouter(<LoginPage />)
    
    await user.type(screen.getByLabelText(/username/i), 'testuser')
    await user.type(screen.getByPlaceholderText(/enter your password/i), 'password123')
    await user.click(screen.getByRole('button', { name: /sign in/i }))
    
    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/dashboard')
    })
    
    expect(localStorage.getItem('authToken')).toBe('test-token')
    expect(localStorage.getItem('authUserId')).toBe('1')
    expect(localStorage.getItem('authUsername')).toBe('testuser')
    expect(localStorage.getItem('authUserRole')).toBe('user')
  })

  it('should navigate to admin page after successful login for admin user', async () => {
    const user = userEvent.setup()
    authAPI.login.mockResolvedValue({
      ok: true,
      token: 'admin-token',
      user: { id: '2', username: 'admin', email: 'admin@example.com', role: 'admin' }
    })

    renderWithRouter(<LoginPage />)
    
    await user.type(screen.getByLabelText(/username/i), 'admin')
    await user.type(screen.getByPlaceholderText(/enter your password/i), 'adminpass')
    await user.click(screen.getByRole('button', { name: /sign in/i }))
    
    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/admin')
    })
  })

  it('should show loading state during login', async () => {
    const user = userEvent.setup()
    authAPI.login.mockImplementation(() => new Promise(resolve => setTimeout(() => resolve({
      ok: true,
      token: 'test-token',
      user: { id: '1', username: 'testuser', email: 'test@example.com', role: 'user' }
    }), 100)))

    renderWithRouter(<LoginPage />)
    
    await user.type(screen.getByLabelText(/username/i), 'testuser')
    await user.type(screen.getByPlaceholderText(/enter your password/i), 'password123')
    await user.click(screen.getByRole('button', { name: /sign in/i }))
    
    expect(screen.getByRole('button', { name: /signing in/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /signing in/i })).toBeDisabled()
  })

  // Sad cases - validation
  it('should show error message when username is empty', async () => {
    const user = userEvent.setup()
    renderWithRouter(<LoginPage />)
    
    await user.type(screen.getByPlaceholderText(/enter your password/i), 'password123')
    await user.click(screen.getByRole('button', { name: /sign in/i }))
    
    await waitFor(() => {
      expect(screen.getByText(/please fill in both username and password/i)).toBeInTheDocument()
    })
    
    expect(authAPI.login).not.toHaveBeenCalled()
  })

  it('should show error message when password is empty', async () => {
    const user = userEvent.setup()
    renderWithRouter(<LoginPage />)
    
    await user.type(screen.getByLabelText(/username/i), 'testuser')
    await user.click(screen.getByRole('button', { name: /sign in/i }))
    
    await waitFor(() => {
      expect(screen.getByText(/please fill in both username and password/i)).toBeInTheDocument()
    })
    
    expect(authAPI.login).not.toHaveBeenCalled()
  })

  it('should show error message when both fields are empty', async () => {
    const user = userEvent.setup()
    renderWithRouter(<LoginPage />)
    
    await user.click(screen.getByRole('button', { name: /sign in/i }))
    
    await waitFor(() => {
      expect(screen.getByText(/please fill in both username and password/i)).toBeInTheDocument()
    })
    
    expect(authAPI.login).not.toHaveBeenCalled()
  })

  it('should trim username before validation', async () => {
    const user = userEvent.setup()
    renderWithRouter(<LoginPage />)
    
    await user.type(screen.getByLabelText(/username/i), '  testuser  ')
    await user.type(screen.getByPlaceholderText(/enter your password/i), 'password123')
    await user.click(screen.getByRole('button', { name: /sign in/i }))
    
    await waitFor(() => {
      expect(authAPI.login).toHaveBeenCalledWith({ username: 'testuser', password: 'password123' })
    })
  })

  // Sad cases - API errors
  it('should show error message when login fails', async () => {
    const user = userEvent.setup()
    // Clear any previous mock calls and localStorage
    mockNavigate.mockClear()
    authAPI.login.mockReset() // Use mockReset to completely reset the mock
    localStorage.clear()
    
    // Verify localStorage is empty before test
    expect(localStorage.getItem('authToken')).toBeNull()
    
    // Explicitly set the mock return value - ensure ok is explicitly false (not undefined)
    // Use mockResolvedValueOnce to ensure it only applies to this test
    authAPI.login.mockResolvedValueOnce({
      ok: false,
      message: 'Invalid credentials'
    })

    renderWithRouter(<LoginPage />)
    
    await user.type(screen.getByLabelText(/username/i), 'testuser')
    await user.type(screen.getByPlaceholderText(/enter your password/i), 'wrongpass')
    await user.click(screen.getByRole('button', { name: /sign in/i }))
    
    // Wait for error message to appear
    await waitFor(() => {
      expect(screen.getByText('Invalid credentials')).toBeInTheDocument()
    }, { timeout: 3000 })
    
    // Verify login was called with correct arguments
    expect(authAPI.login).toHaveBeenCalledWith({
      username: 'testuser',
      password: 'wrongpass'
    })
    
    // Verify the mock was called exactly once
    expect(authAPI.login).toHaveBeenCalledTimes(1)
    
    // Wait for all async operations to complete
    await new Promise(resolve => setTimeout(resolve, 500))
    
    // The key assertion: if error message is shown, localStorage should NOT be set
    // This is the most reliable way to verify the error path was taken
    expect(screen.getByText('Invalid credentials')).toBeInTheDocument()
    expect(localStorage.getItem('authToken')).toBeNull()
    expect(localStorage.getItem('authUserId')).toBeNull()
    expect(localStorage.getItem('authUsername')).toBeNull()
    expect(localStorage.getItem('authUserRole')).toBeNull()
    
    // Also verify that the form is still visible (user is still on login page)
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument()
    expect(screen.getByLabelText(/username/i)).toBeInTheDocument()
  })

  it('should show error message when login throws exception', async () => {
    const user = userEvent.setup()
    authAPI.login.mockRejectedValue(new Error('Network error'))

    renderWithRouter(<LoginPage />)
    
    await user.type(screen.getByLabelText(/username/i), 'testuser')
    await user.type(screen.getByPlaceholderText(/enter your password/i), 'password123')
    await user.click(screen.getByRole('button', { name: /sign in/i }))
    
    await waitFor(() => {
      expect(screen.getByText('Network error')).toBeInTheDocument()
    })
  })

  it('should show generic error message when exception has no message', async () => {
    const user = userEvent.setup()
    authAPI.login.mockRejectedValue({})

    renderWithRouter(<LoginPage />)
    
    await user.type(screen.getByLabelText(/username/i), 'testuser')
    await user.type(screen.getByPlaceholderText(/enter your password/i), 'password123')
    await user.click(screen.getByRole('button', { name: /sign in/i }))
    
    await waitFor(() => {
      expect(screen.getByText(/unexpected error/i)).toBeInTheDocument()
    })
  })

  it('should handle error message object with detail property', async () => {
    const user = userEvent.setup()
    authAPI.login.mockResolvedValue({
      ok: false,
      message: { detail: 'Custom error detail' }
    })

    renderWithRouter(<LoginPage />)
    
    await user.type(screen.getByLabelText(/username/i), 'testuser')
    await user.type(screen.getByPlaceholderText(/enter your password/i), 'password123')
    await user.click(screen.getByRole('button', { name: /sign in/i }))
    
    await waitFor(() => {
      expect(screen.getByText('Custom error detail')).toBeInTheDocument()
    })
  })

  // User interactions - navigation
  it('should navigate to register page when register link is clicked', async () => {
    const user = userEvent.setup()
    renderWithRouter(<LoginPage />)
    
    await user.click(screen.getByText('Register'))
    expect(mockNavigate).toHaveBeenCalledWith('/register')
  })

  it('should navigate to forgot password page when forgot password link is clicked', async () => {
    const user = userEvent.setup()
    renderWithRouter(<LoginPage />)
    
    await user.click(screen.getByText('Forget password?'))
    expect(mockNavigate).toHaveBeenCalledWith('/forgot-password')
  })

  // Error message dismissal
  it('should dismiss error message when close button is clicked', async () => {
    const user = userEvent.setup()
    authAPI.login.mockResolvedValue({
      ok: false,
      message: 'Error message'
    })

    renderWithRouter(<LoginPage />)
    
    await user.type(screen.getByLabelText(/username/i), 'testuser')
    await user.type(screen.getByPlaceholderText(/enter your password/i), 'password123')
    await user.click(screen.getByRole('button', { name: /sign in/i }))
    
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

