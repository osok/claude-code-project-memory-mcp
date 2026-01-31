/**
 * Validation functions for user input.
 */

const EMAIL_PATTERN = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
const USERNAME_PATTERN = /^[a-zA-Z][a-zA-Z0-9_]{2,29}$/;

/**
 * Validate an email address format.
 *
 * @param email - The email address to validate
 * @returns True if the email is valid, false otherwise
 *
 * @example
 * validateEmail("user@example.com") // true
 * validateEmail("invalid-email") // false
 */
export function validateEmail(email: string): boolean {
  if (!email || typeof email !== 'string') {
    return false;
  }
  return EMAIL_PATTERN.test(email.trim());
}

/**
 * Validate a username.
 *
 * Username must:
 * - Start with a letter
 * - Be 3-30 characters long
 * - Contain only letters, numbers, and underscores
 *
 * @param username - The username to validate
 * @returns True if the username is valid, false otherwise
 *
 * @example
 * validateUsername("john_doe") // true
 * validateUsername("123invalid") // false
 */
export function validateUsername(username: string): boolean {
  if (!username || typeof username !== 'string') {
    return false;
  }
  return USERNAME_PATTERN.test(username);
}

/**
 * Validate a UUID string.
 *
 * @param value - The string to validate as UUID
 * @returns True if the string is a valid UUID, false otherwise
 *
 * @example
 * validateUuid("550e8400-e29b-41d4-a716-446655440000") // true
 * validateUuid("not-a-uuid") // false
 */
export function validateUuid(value: string): boolean {
  if (!value || typeof value !== 'string') {
    return false;
  }
  const uuidPattern =
    /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
  return uuidPattern.test(value);
}

/**
 * Result of task title validation.
 */
export interface ValidationResult {
  isValid: boolean;
  errorMessage?: string;
}

/**
 * Validate a task title.
 *
 * @param title - The title to validate
 * @param minLength - Minimum allowed length (default: 3)
 * @param maxLength - Maximum allowed length (default: 200)
 * @returns Validation result with isValid and optional error message
 *
 * @example
 * validateTaskTitle("Fix bug") // { isValid: true }
 * validateTaskTitle("Ab") // { isValid: false, errorMessage: "..." }
 */
export function validateTaskTitle(
  title: string,
  minLength = 3,
  maxLength = 200
): ValidationResult {
  if (!title || typeof title !== 'string') {
    return { isValid: false, errorMessage: 'Title is required' };
  }

  const trimmed = title.trim();
  if (trimmed.length < minLength) {
    return {
      isValid: false,
      errorMessage: `Title must be at least ${minLength} characters`,
    };
  }
  if (trimmed.length > maxLength) {
    return {
      isValid: false,
      errorMessage: `Title must be at most ${maxLength} characters`,
    };
  }

  return { isValid: true };
}

/**
 * Password validation options.
 */
export interface PasswordOptions {
  minLength?: number;
  requireUppercase?: boolean;
  requireLowercase?: boolean;
  requireDigit?: boolean;
  requireSpecial?: boolean;
}

/**
 * Result of password validation.
 */
export interface PasswordValidationResult {
  isValid: boolean;
  errors: string[];
}

/**
 * Validate a password against security requirements.
 *
 * @param password - The password to validate
 * @param options - Validation options
 * @returns Validation result with isValid and list of errors
 *
 * @example
 * validatePassword("SecurePass1") // { isValid: true, errors: [] }
 * validatePassword("weak") // { isValid: false, errors: [...] }
 */
export function validatePassword(
  password: string,
  options: PasswordOptions = {}
): PasswordValidationResult {
  const {
    minLength = 8,
    requireUppercase = true,
    requireLowercase = true,
    requireDigit = true,
    requireSpecial = false,
  } = options;

  const errors: string[] = [];

  if (!password) {
    return { isValid: false, errors: ['Password is required'] };
  }

  if (password.length < minLength) {
    errors.push(`Password must be at least ${minLength} characters`);
  }

  if (requireUppercase && !/[A-Z]/.test(password)) {
    errors.push('Password must contain at least one uppercase letter');
  }

  if (requireLowercase && !/[a-z]/.test(password)) {
    errors.push('Password must contain at least one lowercase letter');
  }

  if (requireDigit && !/\d/.test(password)) {
    errors.push('Password must contain at least one digit');
  }

  if (requireSpecial && !/[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]/.test(password)) {
    errors.push('Password must contain at least one special character');
  }

  return { isValid: errors.length === 0, errors };
}

/**
 * Sanitize user input by stripping whitespace and limiting length.
 *
 * @param value - The input to sanitize
 * @param maxLength - Maximum allowed length (default: 1000)
 * @returns Sanitized string
 */
export function sanitizeInput(value: string, maxLength = 1000): string {
  if (!value) {
    return '';
  }
  return value.trim().slice(0, maxLength);
}
