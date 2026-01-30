// src/pages/Admin/__tests__/AdminKeyManagement.test.jsx
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import AdminKeyManagement from '@src/pages/Admin/AdminKeyManagement'

// Mock admin API
vi.mock('@src/api/admin', () => ({
  batchGenerateKeys: vi.fn(),
  listLicenseKeys: vi.fn(),
  deleteLicenseKey: vi.fn(),
}))

// Import after mocking
import * as adminAPI from '@src/api/admin'

describe('AdminKeyManagement', () => {
  let clipboardWriteTextSpy

  beforeEach(() => {
    vi.clearAllMocks()
    // Ensure navigator.clipboard exists before spying
    if (!navigator.clipboard) {
      Object.defineProperty(navigator, 'clipboard', {
        value: {
          writeText: vi.fn().mockResolvedValue(undefined),
        },
        writable: true,
        configurable: true,
      })
    }
    // Mock navigator.clipboard.writeText
    clipboardWriteTextSpy = vi.spyOn(navigator.clipboard, 'writeText').mockResolvedValue(undefined)
  })

  afterEach(() => {
    if (clipboardWriteTextSpy) {
      clipboardWriteTextSpy.mockRestore()
    }
  })

  // Happy cases - rendering
  it('should render key management page', () => {
    adminAPI.listLicenseKeys.mockResolvedValue({
      ok: true,
      data: { items: [], total: 0 },
    })

    render(<AdminKeyManagement />)

    expect(screen.getByText('Batch Generate License Keys')).toBeInTheDocument()
  })

  it('should display license keys list', async () => {
    const mockKeys = [
      {
        id: '1',
        key: 'FAT-XXXX-XXXX-1234',
        keyType: 'paid',
        is_used: false,
        created_at: '2024-01-01T00:00:00Z',
        preview: 'FAT-****-****-1234',
      },
    ]

    adminAPI.listLicenseKeys.mockResolvedValue({
      ok: true,
      data: { items: mockKeys, total: 1 },
    })

    render(<AdminKeyManagement />)

    await waitFor(() => {
      expect(screen.getByText('FAT-****-****-1234')).toBeInTheDocument()
    })
  })

  // Generate keys functionality
  it('should generate keys when form is submitted', async () => {
    const user = userEvent.setup()
    const mockGeneratedKeys = [
      {
        id: '1',
        key: 'FAT-XXXX-XXXX-1234',
        keyType: 'paid',
        expiresAt: null,
      },
    ]

    adminAPI.listLicenseKeys.mockResolvedValue({
      ok: true,
      data: { items: [], total: 0 },
    })
    adminAPI.batchGenerateKeys.mockResolvedValue({
      ok: true,
      data: { keys: mockGeneratedKeys },
    })

    render(<AdminKeyManagement />)

    // Use getByPlaceholderText since label doesn't have 'for' attribute
    const countInput = screen.getByPlaceholderText(/1-200/i)
    await user.clear(countInput)
    await user.type(countInput, '5')

    const generateButton = screen.getByRole('button', { name: /generate/i })
    await user.click(generateButton)

    await waitFor(() => {
      expect(adminAPI.batchGenerateKeys).toHaveBeenCalledWith({
        count: 5,
        keyType: 'paid',
        expireDays: null,
        prefix: 'FAT',
      })
    })
  })

  it('should validate count input (1-200)', async () => {
    const user = userEvent.setup()
    adminAPI.listLicenseKeys.mockResolvedValue({
      ok: true,
      data: { items: [], total: 0 },
    })

    render(<AdminKeyManagement />)

    // Use getByPlaceholderText since label doesn't have 'for' attribute
    const countInput = screen.getByPlaceholderText(/1-200/i)
    await user.clear(countInput)
    await user.type(countInput, '201')

    const generateButton = screen.getByRole('button', { name: /generate/i })
    await user.click(generateButton)

    await waitFor(() => {
      expect(screen.getByText('Count must be between 1-200')).toBeInTheDocument()
    })

    expect(adminAPI.batchGenerateKeys).not.toHaveBeenCalled()
  })

  it('should validate expiry days input (1-3650)', async () => {
    const user = userEvent.setup()
    adminAPI.listLicenseKeys.mockResolvedValue({
      ok: true,
      data: { items: [], total: 0 },
    })

    render(<AdminKeyManagement />)

    // Use getByPlaceholderText since label doesn't have 'for' attribute
    const expireDaysInput = screen.getByPlaceholderText(/Leave empty for permanent/i)
    await user.type(expireDaysInput, '5000')

    const generateButton = screen.getByRole('button', { name: /generate/i })
    await user.click(generateButton)

    await waitFor(() => {
      expect(screen.getByText('Expiry days must be between 1-3650')).toBeInTheDocument()
    })

    expect(adminAPI.batchGenerateKeys).not.toHaveBeenCalled()
  })

  it('should generate keys with expiry days', async () => {
    const user = userEvent.setup()
    const mockGeneratedKeys = [
      {
        id: '1',
        key: 'FAT-XXXX-XXXX-1234',
        keyType: 'paid',
        expiresAt: '2025-01-01T00:00:00Z',
      },
    ]

    adminAPI.listLicenseKeys.mockResolvedValue({
      ok: true,
      data: { items: [], total: 0 },
    })
    adminAPI.batchGenerateKeys.mockResolvedValue({
      ok: true,
      data: { keys: mockGeneratedKeys },
    })

    render(<AdminKeyManagement />)

    // Use getByPlaceholderText since label doesn't have 'for' attribute
    const countInput = screen.getByPlaceholderText(/1-200/i)
    await user.clear(countInput)
    await user.type(countInput, '1')

    const expireDaysInput = screen.getByPlaceholderText(/Leave empty for permanent/i)
    await user.type(expireDaysInput, '30')

    const generateButton = screen.getByRole('button', { name: /generate/i })
    await user.click(generateButton)

    await waitFor(() => {
      expect(adminAPI.batchGenerateKeys).toHaveBeenCalledWith({
        count: 1,
        keyType: 'paid',
        expireDays: 30,
        prefix: 'FAT',
      })
    })
  })

  // Copy key functionality
  it('should copy key to clipboard when copy button is clicked', async () => {
    const user = userEvent.setup()
    const mockGeneratedKeys = [
      {
        id: '1',
        key: 'FAT-XXXX-XXXX-1234',
        keyType: 'paid',
        expiresAt: null,
      },
    ]

    adminAPI.listLicenseKeys.mockResolvedValue({
      ok: true,
      data: { items: [], total: 0 },
    })
    adminAPI.batchGenerateKeys.mockResolvedValue({
      ok: true,
      data: { keys: mockGeneratedKeys },
    })

    render(<AdminKeyManagement />)

    // Use getByPlaceholderText since label doesn't have 'for' attribute
    const countInput = screen.getByPlaceholderText(/1-200/i)
    await user.clear(countInput)
    await user.type(countInput, '1')

    const generateButton = screen.getByRole('button', { name: /generate/i })
    await user.click(generateButton)

    await waitFor(() => {
      expect(screen.getByText('FAT-XXXX-XXXX-1234')).toBeInTheDocument()
    })

    // Use getAllByRole and find the "Copy" button (not "Copy All")
    const copyButtons = screen.getAllByRole('button', { name: /copy/i })
    const copyButton = copyButtons.find(btn => btn.textContent === 'Copy')
    expect(copyButton).toBeInTheDocument()
    await user.click(copyButton)

    await waitFor(() => {
      expect(clipboardWriteTextSpy).toHaveBeenCalledWith('FAT-XXXX-XXXX-1234')
      expect(screen.getByText('Key copied to clipboard.')).toBeInTheDocument()
    })
  })

  // Delete key functionality
  it('should delete key when delete button is clicked', async () => {
    const user = userEvent.setup()
    const mockKeys = [
      {
        id: '1',
        key: 'FAT-XXXX-XXXX-1234',
        keyType: 'paid',
        is_used: false,
        created_at: '2024-01-01T00:00:00Z',
        preview: 'FAT-****-****-1234',
      },
    ]

    adminAPI.listLicenseKeys.mockResolvedValue({
      ok: true,
      data: { items: mockKeys, total: 1 },
    })
    adminAPI.deleteLicenseKey.mockResolvedValue({ ok: true })

    render(<AdminKeyManagement />)

    await waitFor(() => {
      expect(screen.getByText('FAT-****-****-1234')).toBeInTheDocument()
    })

    const deleteButton = screen.getByRole('button', { name: /delete/i })
    await user.click(deleteButton)

    await waitFor(() => {
      expect(adminAPI.deleteLicenseKey).toHaveBeenCalledWith('1')
      expect(screen.getByText('License key deleted successfully.')).toBeInTheDocument()
    })
  })

  // Status filter
  it('should filter keys by status', async () => {
    const user = userEvent.setup()
    adminAPI.listLicenseKeys.mockResolvedValue({
      ok: true,
      data: { items: [], total: 0 },
    })

    render(<AdminKeyManagement />)

    await waitFor(() => {
      expect(adminAPI.listLicenseKeys).toHaveBeenCalled()
    })

    const unusedFilter = screen.getByRole('button', { name: /unused/i })
    await user.click(unusedFilter)

    await waitFor(() => {
      expect(adminAPI.listLicenseKeys).toHaveBeenCalledWith(
        expect.objectContaining({ is_used: false })
      )
    })
  })

  // Pagination
  it('should handle pagination', async () => {
    const user = userEvent.setup()
    // Provide some keys so pagination is displayed (pagination only shows when keys.length > 0)
    const mockKeys = Array.from({ length: 20 }, (_, i) => ({
      id: `key-${i}`,
      key: `FAT-XXXX-XXXX-${i}`,
      keyType: 'paid',
      is_used: false,
      created_at: '2024-01-01T00:00:00Z',
      preview: `FAT-****-****-${i}`,
    }))

    adminAPI.listLicenseKeys.mockResolvedValue({
      ok: true,
      data: { items: mockKeys, total: 50 },
    })

    render(<AdminKeyManagement />)

    await waitFor(() => {
      // Pagination info format: "Page 1 / 3 (Total: 50 keys)"
      expect(screen.getByText(/Page 1/i)).toBeInTheDocument()
    })

    const nextButton = screen.getByRole('button', { name: /next/i })
    await user.click(nextButton)

    await waitFor(() => {
      expect(adminAPI.listLicenseKeys).toHaveBeenCalledWith(
        expect.objectContaining({ offset: 20 })
      )
    })
  })

  // Error handling
  it('should display error message when generating keys fails', async () => {
    const user = userEvent.setup()
    adminAPI.listLicenseKeys.mockResolvedValue({
      ok: true,
      data: { items: [], total: 0 },
    })
    adminAPI.batchGenerateKeys.mockResolvedValue({
      ok: false,
      message: 'Failed to generate keys',
    })

    render(<AdminKeyManagement />)

    // Use getByPlaceholderText since label doesn't have 'for' attribute
    const countInput = screen.getByPlaceholderText(/1-200/i)
    await user.clear(countInput)
    await user.type(countInput, '1')

    const generateButton = screen.getByRole('button', { name: /generate/i })
    await user.click(generateButton)

    await waitFor(() => {
      expect(screen.getByText('Failed to generate keys')).toBeInTheDocument()
    })
  })

  it('should display error message when loading keys fails', async () => {
    adminAPI.listLicenseKeys.mockResolvedValue({
      ok: false,
      message: 'Failed to load keys',
    })

    render(<AdminKeyManagement />)

    await waitFor(() => {
      expect(screen.getByText('Failed to load keys')).toBeInTheDocument()
    })
  })
})

