/**
 * Task model with status and priority enums.
 */

import { generateId } from '../utils/helpers';

/**
 * Status values for tasks.
 */
export enum TaskStatus {
  PENDING = 'pending',
  IN_PROGRESS = 'in_progress',
  BLOCKED = 'blocked',
  COMPLETED = 'completed',
  CANCELLED = 'cancelled',
}

/**
 * Priority levels for tasks.
 */
export enum TaskPriority {
  LOW = 1,
  MEDIUM = 2,
  HIGH = 3,
  CRITICAL = 4,
}

/**
 * Task interface defining the structure of a task.
 */
export interface ITask {
  id: string;
  title: string;
  description: string;
  projectId: string;
  assigneeId?: string;
  status: TaskStatus;
  priority: TaskPriority;
  createdAt: Date;
  updatedAt: Date;
  dueDate?: Date;
  tags: string[];
}

/**
 * Represents a task in the system.
 *
 * A task belongs to a project and can be assigned to a user.
 * Tasks have status and priority tracking with timestamps.
 */
export class Task implements ITask {
  public id: string;
  public title: string;
  public description: string;
  public projectId: string;
  public assigneeId?: string;
  public status: TaskStatus;
  public priority: TaskPriority;
  public createdAt: Date;
  public updatedAt: Date;
  public dueDate?: Date;
  public tags: string[];

  /**
   * Create a new Task instance.
   *
   * @param title - Short description of the task
   * @param projectId - ID of the project this task belongs to
   * @param options - Additional task options
   */
  constructor(
    title: string,
    projectId: string,
    options: Partial<Omit<ITask, 'title' | 'projectId'>> = {}
  ) {
    this.id = options.id ?? generateId();
    this.title = title;
    this.projectId = projectId;
    this.description = options.description ?? '';
    this.assigneeId = options.assigneeId;
    this.status = options.status ?? TaskStatus.PENDING;
    this.priority = options.priority ?? TaskPriority.MEDIUM;
    this.createdAt = options.createdAt ?? new Date();
    this.updatedAt = options.updatedAt ?? new Date();
    this.dueDate = options.dueDate;
    this.tags = options.tags ?? [];
  }

  /**
   * Mark the task as completed and update timestamp.
   */
  markComplete(): void {
    this.status = TaskStatus.COMPLETED;
    this.updatedAt = new Date();
  }

  /**
   * Mark the task as blocked.
   *
   * @param reason - Optional reason for the block
   */
  markBlocked(reason?: string): void {
    this.status = TaskStatus.BLOCKED;
    this.updatedAt = new Date();
    if (reason) {
      this.description = `${this.description}\n\nBlocked: ${reason}`;
    }
  }

  /**
   * Assign the task to a user.
   *
   * @param userId - The ID of the user to assign
   */
  assignTo(userId: string): void {
    this.assigneeId = userId;
    this.updatedAt = new Date();
  }

  /**
   * Add a tag to the task.
   *
   * @param tag - The tag to add
   * @returns True if tag was added, false if already exists
   */
  addTag(tag: string): boolean {
    const normalizedTag = tag.toLowerCase().trim();
    if (!this.tags.includes(normalizedTag)) {
      this.tags.push(normalizedTag);
      this.updatedAt = new Date();
      return true;
    }
    return false;
  }

  /**
   * Remove a tag from the task.
   *
   * @param tag - The tag to remove
   * @returns True if tag was removed, false if not found
   */
  removeTag(tag: string): boolean {
    const normalizedTag = tag.toLowerCase().trim();
    const index = this.tags.indexOf(normalizedTag);
    if (index !== -1) {
      this.tags.splice(index, 1);
      this.updatedAt = new Date();
      return true;
    }
    return false;
  }

  /**
   * Check if the task is past its due date.
   */
  get isOverdue(): boolean {
    if (!this.dueDate) {
      return false;
    }
    return new Date() > this.dueDate && this.status !== TaskStatus.COMPLETED;
  }

  /**
   * Check if the task is in an active state.
   */
  get isActive(): boolean {
    return (
      this.status === TaskStatus.PENDING ||
      this.status === TaskStatus.IN_PROGRESS
    );
  }

  /**
   * Convert task to a plain object.
   */
  toJSON(): ITask {
    return {
      id: this.id,
      title: this.title,
      description: this.description,
      projectId: this.projectId,
      assigneeId: this.assigneeId,
      status: this.status,
      priority: this.priority,
      createdAt: this.createdAt,
      updatedAt: this.updatedAt,
      dueDate: this.dueDate,
      tags: [...this.tags],
    };
  }

  /**
   * Create a Task from a plain object.
   *
   * @param data - The data to create from
   */
  static fromJSON(data: ITask): Task {
    return new Task(data.title, data.projectId, {
      id: data.id,
      description: data.description,
      assigneeId: data.assigneeId,
      status: data.status,
      priority: data.priority,
      createdAt: new Date(data.createdAt),
      updatedAt: new Date(data.updatedAt),
      dueDate: data.dueDate ? new Date(data.dueDate) : undefined,
      tags: data.tags,
    });
  }
}
