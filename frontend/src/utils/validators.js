// src/util/validators.js

/**
 * Password complexity validation:
 * - At least 8 characters
 * - Must contain at least two of the following four types: uppercase letters / lowercase letters / digits / special characters
 */
export function validatePasswordComplexity(pwd) {
  if (!pwd || pwd.length < 8) {
    return "Password must be at least 8 characters long and contain at least two of: uppercase, lowercase, number, special character.";
  }

  const hasLower = /[a-z]/.test(pwd);
  const hasUpper = /[A-Z]/.test(pwd);
  const hasDigit = /[0-9]/.test(pwd);
  const hasSpecial = /[^a-zA-Z0-9]/.test(pwd);

  const typeCount = [hasLower, hasUpper, hasDigit, hasSpecial].filter(Boolean).length;

  if (typeCount < 2) {
    return "Password must contain at least two of: uppercase, lowercase, number, special character.";
  }

  return null; // Validation passed
}

/**
 * Email format validation
 */
export function validateEmailFormat(email) {
  if (!email) return "Email is required.";

  const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!re.test(email)) return "Please enter a valid email address.";

  return null;
}