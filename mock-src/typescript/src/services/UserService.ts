/**
 * User service for managing users.
 */

import { User, UserRole, IUser } from '../models/User';
import {
  validateEmail,
  validateUsername,
  validatePassword,
} from '../utils/validators';
import { generateId } from '../utils/helpers';

/**
 * Service error base class.
 */
export class ServiceError extends Error {
  constructor(
    message: string,
    public code: string = 'SERVICE_ERROR'
  ) {
    super(message);
    this.name = 'ServiceError';
  }
}

/**
 * Not found error.
 */
export class NotFoundError extends ServiceError {
  constructor(entityType: string, entityId: string) {
    super(`${entityType} with ID ${entityId} not found`, 'NOT_FOUND');
    this.name = 'NotFoundError';
  }
}

/**
 * Validation error.
 */
export class ValidationError extends ServiceError {
  constructor(
    public field: string,
    message: string
  ) {
    super(`Validation failed for ${field}: ${message}`, 'VALIDATION_ERROR');
    this.name = 'ValidationError';
  }
}

/**
 * Authorization error.
 */
export class AuthorizationError extends ServiceError {
  constructor(action: string, resource: string) {
    super(`Not authorized to ${action} ${resource}`, 'AUTHORIZATION_ERROR');
    this.name = 'AuthorizationError';
  }
}

/**
 * Options for creating a user.
 */
export interface CreateUserOptions {
  displayName?: string;
  role?: UserRole;
}

/**
 * Service for user management operations.
 *
 * Handles user creation, authentication, and authorization.
 */
export class UserService {
  private users: Map<string, User> = new Map();
  private emailIndex: Map<string, string> = new Map();
  private usernameIndex: Map<string, string> = new Map();
  private passwordHashes: Map<string, string> = new Map();
  private sessionTokens: Map<string, string> = new Map();

  /**
   * Create a new user account.
   *
   * @param username - Unique username for login
   * @param email - User's email address
   * @param password - Account password
   * @param options - Additional user options
   * @returns The created user
   * @throws ValidationError if any field is invalid
   */
  createUser(
    username: string,
    email: string,
    password: string,
    options: CreateUserOptions = {}
  ): User {
    // Validate inputs
    if (!validateUsername(username)) {
      throw new ValidationError('username', 'Invalid username format');
    }

    if (!validateEmail(email)) {
      throw new ValidationError('email', 'Invalid email format');
    }

    const passwordValidation = validatePassword(password);
    if (!passwordValidation.isValid) {
      throw new ValidationError('password', passwordValidation.errors.join('; '));
    }

    // Check uniqueness
    if (this.emailIndex.has(email.toLowerCase())) {
      throw new ValidationError('email', 'Email already registered');
    }

    if (this.usernameIndex.has(username.toLowerCase())) {
      throw new ValidationError('username', 'Username already taken');
    }

    // Create user
    const user = new User(username, email, {
      displayName: options.displayName || username,
      role: options.role,
    });

    this.users.set(user.id, user);
    this.emailIndex.set(email.toLowerCase(), user.id);
    this.usernameIndex.set(username.toLowerCase(), user.id);
    this.passwordHashes.set(user.id, this.hashPassword(password));

    return user;
  }

  /**
   * Get a user by ID.
   *
   * @param userId - The user's unique identifier
   * @returns The user
   * @throws NotFoundError if user doesn't exist
   */
  getUser(userId: string): User {
    const user = this.users.get(userId);
    if (!user) {
      throw new NotFoundError('User', userId);
    }
    return user;
  }

  /**
   * Get a user by email address.
   *
   * @param email - The email to look up
   * @returns The user
   * @throws NotFoundError if user doesn't exist
   */
  getUserByEmail(email: string): User {
    const userId = this.emailIndex.get(email.toLowerCase());
    if (!userId) {
      throw new NotFoundError('User', email);
    }
    return this.getUser(userId);
  }

  /**
   * Get a user by username.
   *
   * @param username - The username to look up
   * @returns The user
   * @throws NotFoundError if user doesn't exist
   */
  getUserByUsername(username: string): User {
    const userId = this.usernameIndex.get(username.toLowerCase());
    if (!userId) {
      throw new NotFoundError('User', username);
    }
    return this.getUser(userId);
  }

  /**
   * Update a user's profile.
   *
   * @param userId - The user to update
   * @param displayName - New display name
   * @param email - New email address
   * @returns The updated user
   */
  updateUser(
    userId: string,
    displayName?: string,
    email?: string
  ): User {
    const user = this.getUser(userId);

    if (displayName !== undefined) {
      user.displayName = displayName;
    }

    if (email !== undefined) {
      if (!validateEmail(email)) {
        throw new ValidationError('email', 'Invalid email format');
      }
      user.email = email;
    }

    return user;
  }

  /**
   * Deactivate a user account.
   *
   * @param userId - The user to deactivate
   * @param actorId - The user performing the action
   * @returns The deactivated user
   * @throws AuthorizationError if actor lacks permission
   */
  deactivateUser(userId: string, actorId: string): User {
    const actor = this.getUser(actorId);
    if (!actor.isAdmin) {
      throw new AuthorizationError('deactivate', 'user accounts');
    }

    const user = this.getUser(userId);
    user.deactivate();
    return user;
  }

  /**
   * Authenticate a user and return a session token.
   *
   * @param username - The username to authenticate
   * @param password - The password to verify
   * @returns Session token if successful, null if failed
   */
  authenticate(username: string, password: string): string | null {
    let user: User;
    try {
      user = this.getUserByUsername(username);
    } catch {
      return null;
    }

    if (!user.isActive) {
      return null;
    }

    const storedHash = this.passwordHashes.get(user.id);
    if (!storedHash || this.hashPassword(password) !== storedHash) {
      return null;
    }

    // Create session token
    const token = this.generateToken();
    this.sessionTokens.set(token, user.id);

    // Record login
    user.recordLogin();

    return token;
  }

  /**
   * Authenticate a user asynchronously.
   *
   * @param username - The username to authenticate
   * @param password - The password to verify
   * @returns Promise resolving to session token or null
   */
  async authenticateAsync(
    username: string,
    password: string
  ): Promise<string | null> {
    await new Promise((resolve) => setTimeout(resolve, 10));
    return this.authenticate(username, password);
  }

  /**
   * Validate a session token and return the user.
   *
   * @param token - The session token to validate
   * @returns The user if valid, null otherwise
   */
  validateToken(token: string): User | null {
    const userId = this.sessionTokens.get(token);
    if (!userId) {
      return null;
    }

    try {
      const user = this.getUser(userId);
      return user.isActive ? user : null;
    } catch {
      return null;
    }
  }

  /**
   * Invalidate a session token.
   *
   * @param token - The token to invalidate
   * @returns True if token was valid and invalidated
   */
  logout(token: string): boolean {
    if (this.sessionTokens.has(token)) {
      this.sessionTokens.delete(token);
      return true;
    }
    return false;
  }

  /**
   * Change a user's password.
   *
   * @param userId - The user's ID
   * @param oldPassword - Current password for verification
   * @param newPassword - New password to set
   * @returns True if password was changed
   * @throws ValidationError if new password is invalid
   * @throws AuthorizationError if old password is wrong
   */
  changePassword(
    userId: string,
    oldPassword: string,
    newPassword: string
  ): boolean {
    const user = this.getUser(userId);

    const storedHash = this.passwordHashes.get(user.id);
    if (this.hashPassword(oldPassword) !== storedHash) {
      throw new AuthorizationError('change', 'password');
    }

    const passwordValidation = validatePassword(newPassword);
    if (!passwordValidation.isValid) {
      throw new ValidationError('password', passwordValidation.errors.join('; '));
    }

    this.passwordHashes.set(user.id, this.hashPassword(newPassword));
    return true;
  }

  /**
   * Promote a user to a higher role.
   *
   * @param userId - The user to promote
   * @param newRole - The new role to assign
   * @param actorId - The user performing the promotion
   * @returns The updated user
   * @throws AuthorizationError if actor lacks permission
   */
  promoteUser(userId: string, newRole: UserRole, actorId: string): User {
    const actor = this.getUser(actorId);
    if (!actor.isAdmin) {
      throw new AuthorizationError('promote', 'users');
    }

    const user = this.getUser(userId);
    user.promoteTo(newRole);
    return user;
  }

  /**
   * Get all admin users.
   */
  getAdmins(): User[] {
    return Array.from(this.users.values()).filter((u) => u.isAdmin);
  }

  /**
   * Search users by name, email, or username.
   *
   * @param query - Search text
   * @returns Matching users
   */
  searchUsers(query: string): User[] {
    const queryLower = query.toLowerCase();
    return Array.from(this.users.values()).filter(
      (u) =>
        u.username.toLowerCase().includes(queryLower) ||
        u.email.toLowerCase().includes(queryLower) ||
        u.displayName.toLowerCase().includes(queryLower)
    );
  }

  /**
   * Get count of active users.
   */
  get activeUserCount(): number {
    return Array.from(this.users.values()).filter((u) => u.isActive).length;
  }

  private hashPassword(password: string): string {
    // Simple hash for demo purposes
    let hash = 0;
    for (let i = 0; i < password.length; i++) {
      const char = password.charCodeAt(i);
      hash = (hash << 5) - hash + char;
      hash = hash & hash;
    }
    return hash.toString(16);
  }

  private generateToken(): string {
    return generateId() + generateId();
  }
}
