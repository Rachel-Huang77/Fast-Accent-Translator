// Test setup file
import { expect, afterEach } from 'vitest'
import { cleanup } from '@testing-library/react'
import * as matchers from '@testing-library/jest-dom/matchers'

// Extend Vitest's expect with jest-dom matchers
expect.extend(matchers)

// Global error handler for unhandled promise rejections
// This helps prevent test failures from expected errors in error handling tests
if (typeof window !== 'undefined') {
  window.addEventListener('unhandledrejection', (event) => {
    // Only prevent default if it's a known test error
    // This allows real errors to still be reported
    const errorMessage = event.reason?.message || ''
    if (errorMessage === 'Failed to load' || errorMessage === 'Failed to create') {
      event.preventDefault()
      event.stopPropagation()
    }
  }, true) // Use capture phase
}

// Cleanup after each test
afterEach(() => {
  cleanup()
})

