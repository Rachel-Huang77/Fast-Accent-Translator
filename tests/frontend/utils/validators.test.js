// tests/frontend/utils/validators.test.js
import { describe, it, expect } from 'vitest'
import { validatePasswordComplexity, validateEmailFormat } from '@src/utils/validators'

describe('validatePasswordComplexity', () => {
  // Happy cases
  it('should return null for valid password with uppercase, lowercase, and digit', () => {
    expect(validatePasswordComplexity('Password123')).toBeNull()
  })

  it('should return null for valid password with uppercase, lowercase, and special character', () => {
    expect(validatePasswordComplexity('Password@')).toBeNull()
  })

  it('should return null for valid password with lowercase, digit, and special character', () => {
    expect(validatePasswordComplexity('password123!')).toBeNull()
  })

  it('should return null for valid password with all four types', () => {
    expect(validatePasswordComplexity('Password123!')).toBeNull()
  })

  it('should return null for valid password with exactly 8 characters', () => {
    expect(validatePasswordComplexity('Pass123!')).toBeNull()
  })

  // Sad cases - length validation
  it('should return error message for password shorter than 8 characters', () => {
    const result = validatePasswordComplexity('Pass1!')
    expect(result).toBe('Password must be at least 8 characters long and contain at least two of: uppercase, lowercase, number, special character.')
  })

  it('should return error message for empty password', () => {
    const result = validatePasswordComplexity('')
    expect(result).toBe('Password must be at least 8 characters long and contain at least two of: uppercase, lowercase, number, special character.')
  })

  it('should return error message for null password', () => {
    const result = validatePasswordComplexity(null)
    expect(result).toBe('Password must be at least 8 characters long and contain at least two of: uppercase, lowercase, number, special character.')
  })

  it('should return error message for undefined password', () => {
    const result = validatePasswordComplexity(undefined)
    expect(result).toBe('Password must be at least 8 characters long and contain at least two of: uppercase, lowercase, number, special character.')
  })

  // Sad cases - complexity validation
  it('should return error message for password with only lowercase letters', () => {
    const result = validatePasswordComplexity('passwordonly')
    expect(result).toBe('Password must contain at least two of: uppercase, lowercase, number, special character.')
  })

  it('should return error message for password with only uppercase letters', () => {
    const result = validatePasswordComplexity('PASSWORDONLY')
    expect(result).toBe('Password must contain at least two of: uppercase, lowercase, number, special character.')
  })

  it('should return error message for password with only digits', () => {
    const result = validatePasswordComplexity('12345678')
    expect(result).toBe('Password must contain at least two of: uppercase, lowercase, number, special character.')
  })

  it('should return error message for password with only special characters', () => {
    const result = validatePasswordComplexity('!@#$%^&*')
    expect(result).toBe('Password must contain at least two of: uppercase, lowercase, number, special character.')
  })

  it('should return error message for password with only one type (lowercase + digit but less than 8 chars)', () => {
    const result = validatePasswordComplexity('pass123')
    expect(result).toBe('Password must be at least 8 characters long and contain at least two of: uppercase, lowercase, number, special character.')
  })

  // Edge cases
  it('should handle password with exactly two types (lowercase + uppercase)', () => {
    expect(validatePasswordComplexity('Password')).toBeNull()
  })

  it('should handle password with exactly two types (lowercase + digit)', () => {
    expect(validatePasswordComplexity('password123')).toBeNull()
  })

  it('should handle password with exactly two types (lowercase + special)', () => {
    expect(validatePasswordComplexity('password!')).toBeNull()
  })

  it('should handle password with exactly two types (uppercase + digit)', () => {
    expect(validatePasswordComplexity('PASSWORD123')).toBeNull()
  })

  it('should handle password with exactly two types (uppercase + special)', () => {
    expect(validatePasswordComplexity('PASSWORD!')).toBeNull()
  })

  it('should handle password with exactly two types (digit + special)', () => {
    expect(validatePasswordComplexity('12345678!')).toBeNull()
  })
})

describe('validateEmailFormat', () => {
  // Happy cases
  it('should return null for valid email address', () => {
    expect(validateEmailFormat('user@example.com')).toBeNull()
  })

  it('should return null for valid email with subdomain', () => {
    expect(validateEmailFormat('user@mail.example.com')).toBeNull()
  })

  it('should return null for valid email with numbers', () => {
    expect(validateEmailFormat('user123@example.com')).toBeNull()
  })

  it('should return null for valid email with plus sign', () => {
    expect(validateEmailFormat('user+tag@example.com')).toBeNull()
  })

  it('should return null for valid email with dots', () => {
    expect(validateEmailFormat('user.name@example.com')).toBeNull()
  })

  // Sad cases
  it('should return error message for empty email', () => {
    const result = validateEmailFormat('')
    expect(result).toBe('Email is required.')
  })

  it('should return error message for null email', () => {
    const result = validateEmailFormat(null)
    expect(result).toBe('Email is required.')
  })

  it('should return error message for undefined email', () => {
    const result = validateEmailFormat(undefined)
    expect(result).toBe('Email is required.')
  })

  it('should return error message for email without @ symbol', () => {
    const result = validateEmailFormat('userexample.com')
    expect(result).toBe('Please enter a valid email address.')
  })

  it('should return error message for email without domain', () => {
    const result = validateEmailFormat('user@')
    expect(result).toBe('Please enter a valid email address.')
  })

  it('should return error message for email without TLD', () => {
    const result = validateEmailFormat('user@example')
    expect(result).toBe('Please enter a valid email address.')
  })

  it('should return error message for email with spaces', () => {
    const result = validateEmailFormat('user @example.com')
    expect(result).toBe('Please enter a valid email address.')
  })

  it('should return error message for email with multiple @ symbols', () => {
    const result = validateEmailFormat('user@@example.com')
    expect(result).toBe('Please enter a valid email address.')
  })

  it('should return error message for email starting with @', () => {
    const result = validateEmailFormat('@example.com')
    expect(result).toBe('Please enter a valid email address.')
  })

  it('should return error message for email ending with @', () => {
    const result = validateEmailFormat('user@')
    expect(result).toBe('Please enter a valid email address.')
  })
})

