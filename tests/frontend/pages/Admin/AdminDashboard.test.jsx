// src/pages/Admin/__tests__/AdminDashboard.test.jsx
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter } from 'react-router-dom'
import AdminDashboard from '@src/pages/Admin/AdminDashboard'

// Mock child components
vi.mock('@src/pages/Admin/AdminUserManagement', () => ({
  default: () => <div>User Management Component</div>
}))

vi.mock('@src/pages/Admin/AdminKeyManagement', () => ({
  default: () => <div>Key Management Component</div>
}))

// Mock auth API
vi.mock('@src/api/auth', () => ({
  logout: vi.fn()
}))

// Mock useNavigate
const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

// Import after mocking
import * as authAPI from '@src/api/auth'

// Helper function to render component with router
const renderWithRouter = (component) => {
  return render(<BrowserRouter>{component}</BrowserRouter>)
}

describe('AdminDashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
    localStorage.setItem('authUsername', 'admin')
    authAPI.logout.mockResolvedValue({ ok: true })
  })

  // Happy cases - rendering
  it('should render admin dashboard with header', () => {
    renderWithRouter(<AdminDashboard />)
    
    // Use getByRole for heading to avoid multiple matches (h1 and span both have "Admin Dashboard")
    expect(screen.getByRole('heading', { name: /admin dashboard/i })).toBeInTheDocument()
    expect(screen.getByText('admin')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /logout/i })).toBeInTheDocument()
  })

  it('should render tab navigation', () => {
    renderWithRouter(<AdminDashboard />)
    
    expect(screen.getByText('User Management')).toBeInTheDocument()
    expect(screen.getByText('Batch Generate License Keys')).toBeInTheDocument()
  })

  it('should show User Management component by default', () => {
    renderWithRouter(<AdminDashboard />)
    
    expect(screen.getByText('User Management Component')).toBeInTheDocument()
    expect(screen.queryByText('Key Management Component')).not.toBeInTheDocument()
  })

  it('should display username from localStorage', () => {
    localStorage.setItem('authUsername', 'testadmin')
    renderWithRouter(<AdminDashboard />)
    
    expect(screen.getByText('testadmin')).toBeInTheDocument()
  })

  it('should display default username when localStorage is empty', () => {
    localStorage.removeItem('authUsername')
    renderWithRouter(<AdminDashboard />)
    
    expect(screen.getByText('admin')).toBeInTheDocument()
  })

  // Tab switching
  it('should switch to Key Management when keys tab is clicked', async () => {
    const user = userEvent.setup()
    renderWithRouter(<AdminDashboard />)
    
    const keysTab = screen.getByText('Batch Generate License Keys')
    await user.click(keysTab)
    
    expect(screen.getByText('Key Management Component')).toBeInTheDocument()
    expect(screen.queryByText('User Management Component')).not.toBeInTheDocument()
  })

  it('should switch back to User Management when users tab is clicked', async () => {
    const user = userEvent.setup()
    renderWithRouter(<AdminDashboard />)
    
    // Switch to keys tab
    const keysTab = screen.getByText('Batch Generate License Keys')
    await user.click(keysTab)
    
    // Switch back to users tab
    const usersTab = screen.getByText('User Management')
    await user.click(usersTab)
    
    expect(screen.getByText('User Management Component')).toBeInTheDocument()
    expect(screen.queryByText('Key Management Component')).not.toBeInTheDocument()
  })

  it('should apply active tab styling', async () => {
    const user = userEvent.setup()
    renderWithRouter(<AdminDashboard />)
    
    const usersTab = screen.getByText('User Management').closest('button')
    const keysTab = screen.getByText('Batch Generate License Keys').closest('button')
    
    // Initially users tab should be active - check className contains 'tabActive'
    expect(usersTab?.className).toContain('tabActive')
    expect(keysTab?.className).not.toContain('tabActive')
    
    // Click keys tab
    await user.click(keysTab)
    
    // Keys tab should now be active
    expect(keysTab?.className).toContain('tabActive')
    expect(usersTab?.className).not.toContain('tabActive')
  })

  // Logout functionality
  it('should logout when logout button is clicked', async () => {
    const user = userEvent.setup()
    localStorage.setItem('authUserId', '123')
    localStorage.setItem('authUsername', 'admin')
    localStorage.setItem('authUserRole', 'admin')
    
    renderWithRouter(<AdminDashboard />)
    
    const logoutButton = screen.getByRole('button', { name: /logout/i })
    await user.click(logoutButton)
    
    expect(authAPI.logout).toHaveBeenCalledTimes(1)
    expect(localStorage.getItem('authUserId')).toBeNull()
    expect(localStorage.getItem('authUsername')).toBeNull()
    expect(localStorage.getItem('authUserRole')).toBeNull()
    expect(mockNavigate).toHaveBeenCalledWith('/login', { replace: true })
  })

  it('should clear localStorage even if logout API fails', async () => {
    const user = userEvent.setup()
    localStorage.setItem('authUserId', '123')
    localStorage.setItem('authUsername', 'admin')
    localStorage.setItem('authUserRole', 'admin')
    
    authAPI.logout.mockResolvedValue({ ok: false })
    
    renderWithRouter(<AdminDashboard />)
    
    const logoutButton = screen.getByRole('button', { name: /logout/i })
    await user.click(logoutButton)
    
    // Should still clear localStorage and navigate
    expect(localStorage.getItem('authUserId')).toBeNull()
    expect(mockNavigate).toHaveBeenCalledWith('/login', { replace: true })
  })

  // Footer
  it('should render footer', () => {
    renderWithRouter(<AdminDashboard />)
    
    expect(screen.getByText('Accent 0')).toBeInTheDocument()
  })
})

