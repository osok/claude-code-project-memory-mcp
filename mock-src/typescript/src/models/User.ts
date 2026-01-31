/**
 * User model with role-based access.
 */

import { generateId } from '../utils/helpers';
import { validateEmail, validateUsername } from '../utils/validators';

/**
 * User roles for access control.
 */
export enum UserRole {
  VIEWER = 'viewer',
  MEMBER = 'member',
  ADMIN = 'admin',
  OWNER = 'owner',
}

/**
 * User interface defining the structure of a user.
 */
export interface IUser {
  id: string;
  username: string;
  email: string;
  displayName: string;
  role: UserRole;
  isActive: boolean;
  createdAt: Date;
  lastLogin?: Date;
}

/**
 * Permission types for users.
 */
type Permission = 'read' | 'write' | 'comment' | 'manage' | 'delete';

/**
 * Mapping of roles to their permissions.
 */
const ROLE_PERMISSIONS: Record<UserRole, Set<Permission>> = {
  [UserRole.VIEWER]: new Set(['read']),
  [UserRole.MEMBER]: new Set(['read', 'write', 'comment']),
  [UserRole.ADMIN]: new Set(['read', 'write', 'comment', 'manage']),
  [UserRole.OWNER]: new Set(['read', 'write', 'comment', 'manage', 'delete']),
};

/**
 * Represents a user in the system.
 *
 * Users can be assigned to tasks and projects. They have roles
 * that determine their access level.
 */
export class User implements IUser {
  public id: string;
  public username: string;
  public email: string;
  public displayName: string;
  public role: UserRole;
  public isActive: boolean;
  public createdAt: Date;
  public lastLogin?: Date;

  /**
   * Create a new User instance.
   *
   * @param username - Unique username for login
   * @param email - User's email address
   * @param options - Additional user options
   * @throws Error if username or email is invalid
   */
  constructor(
    username: string,
    email: string,
    options: Partial<Omit<IUser, 'username' | 'email'>> = {}
  ) {
    if (!validateUsername(username)) {
      throw new Error(`Invalid username: ${username}`);
    }
    if (!validateEmail(email)) {
      throw new Error(`Invalid email: ${email}`);
    }

    this.id = options.id ?? generateId();
    this.username = username;
    this.email = email;
    this.displayName = options.displayName || username;
    this.role = options.role ?? UserRole.MEMBER;
    this.isActive = options.isActive ?? true;
    this.createdAt = options.createdAt ?? new Date();
    this.lastLogin = options.lastLogin;
  }

  /**
   * Check if user has a specific permission.
   *
   * @param permission - The permission to check
   * @returns True if user has the permission
   */
  hasPermission(permission: Permission): boolean {
    const permissions = ROLE_PERMISSIONS[this.role];
    return permissions?.has(permission) ?? false;
  }

  /**
   * Promote user to a higher role.
   *
   * @param newRole - The new role to assign
   * @returns True if promotion was successful
   */
  promoteTo(newRole: UserRole): boolean {
    const roleHierarchy = [
      UserRole.VIEWER,
      UserRole.MEMBER,
      UserRole.ADMIN,
      UserRole.OWNER,
    ];
    const currentIndex = roleHierarchy.indexOf(this.role);
    const newIndex = roleHierarchy.indexOf(newRole);

    if (newIndex > currentIndex) {
      this.role = newRole;
      return true;
    }
    return false;
  }

  /**
   * Deactivate the user account.
   */
  deactivate(): void {
    this.isActive = false;
  }

  /**
   * Record a login event.
   */
  recordLogin(): void {
    this.lastLogin = new Date();
  }

  /**
   * Check if user is an admin or owner.
   */
  get isAdmin(): boolean {
    return this.role === UserRole.ADMIN || this.role === UserRole.OWNER;
  }

  /**
   * Create a guest user with limited access.
   *
   * @param displayName - Name to display for the guest
   * @returns A new guest user instance
   */
  static createGuest(displayName = 'Guest'): User {
    const randomId = Math.random().toString(36).substring(2, 10);
    return new User(`guest_${randomId}`, `guest_${randomId}@example.com`, {
      displayName,
      role: UserRole.VIEWER,
    });
  }

  /**
   * Create a User from a plain object.
   *
   * @param data - The data to create from
   */
  static fromJSON(data: IUser): User {
    return new User(data.username, data.email, {
      id: data.id,
      displayName: data.displayName,
      role: data.role,
      isActive: data.isActive,
      createdAt: new Date(data.createdAt),
      lastLogin: data.lastLogin ? new Date(data.lastLogin) : undefined,
    });
  }

  /**
   * Convert user to a plain object.
   */
  toJSON(): IUser {
    return {
      id: this.id,
      username: this.username,
      email: this.email,
      displayName: this.displayName,
      role: this.role,
      isActive: this.isActive,
      createdAt: this.createdAt,
      lastLogin: this.lastLogin,
    };
  }
}
