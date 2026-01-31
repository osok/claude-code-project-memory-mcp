/**
 * Project model for organizing tasks.
 */

import { generateId } from '../utils/helpers';
import { Task, TaskStatus } from './Task';

/**
 * Project interface defining the structure of a project.
 */
export interface IProject {
  id: string;
  name: string;
  description: string;
  ownerId: string;
  memberIds: string[];
  createdAt: Date;
  updatedAt: Date;
  isArchived: boolean;
}

/**
 * Project summary statistics.
 */
export interface ProjectSummary {
  id: string;
  name: string;
  totalTasks: number;
  completedTasks: number;
  completionPercentage: number;
  statusBreakdown: Record<string, number>;
  hasOverdue: boolean;
  memberCount: number;
}

/**
 * Represents a project containing tasks.
 *
 * Projects organize tasks and have owners and members.
 * They track completion progress based on task statuses.
 */
export class Project implements IProject {
  public id: string;
  public name: string;
  public description: string;
  public ownerId: string;
  public memberIds: string[];
  public createdAt: Date;
  public updatedAt: Date;
  public isArchived: boolean;
  private _tasks: Task[] = [];

  /**
   * Create a new Project instance.
   *
   * @param name - Name of the project
   * @param ownerId - ID of the project owner
   * @param options - Additional project options
   */
  constructor(
    name: string,
    ownerId: string,
    options: Partial<Omit<IProject, 'name' | 'ownerId'>> = {}
  ) {
    this.id = options.id ?? generateId();
    this.name = name;
    this.ownerId = ownerId;
    this.description = options.description ?? '';
    this.memberIds = options.memberIds ?? [];
    this.createdAt = options.createdAt ?? new Date();
    this.updatedAt = options.updatedAt ?? new Date();
    this.isArchived = options.isArchived ?? false;
  }

  /**
   * Add a member to the project.
   *
   * @param userId - ID of the user to add
   * @returns True if member was added, false if already a member
   */
  addMember(userId: string): boolean {
    if (!this.memberIds.includes(userId) && userId !== this.ownerId) {
      this.memberIds.push(userId);
      this.updatedAt = new Date();
      return true;
    }
    return false;
  }

  /**
   * Remove a member from the project.
   *
   * @param userId - ID of the user to remove
   * @returns True if member was removed, false if not a member
   */
  removeMember(userId: string): boolean {
    const index = this.memberIds.indexOf(userId);
    if (index !== -1) {
      this.memberIds.splice(index, 1);
      this.updatedAt = new Date();
      return true;
    }
    return false;
  }

  /**
   * Check if a user is a member or owner.
   *
   * @param userId - ID of the user to check
   * @returns True if user is a member or owner
   */
  isMember(userId: string): boolean {
    return userId === this.ownerId || this.memberIds.includes(userId);
  }

  /**
   * Add a task to the project.
   *
   * @param task - The task to add
   */
  addTask(task: Task): void {
    task.projectId = this.id;
    this._tasks.push(task);
    this.updatedAt = new Date();
  }

  /**
   * Get tasks, optionally filtered by status.
   *
   * @param status - Optional status to filter by
   * @returns List of tasks matching the criteria
   */
  getTasks(status?: TaskStatus): Task[] {
    if (status === undefined) {
      return [...this._tasks];
    }
    return this._tasks.filter((t) => t.status === status);
  }

  /**
   * Archive the project.
   */
  archive(): void {
    this.isArchived = true;
    this.updatedAt = new Date();
  }

  /**
   * Unarchive the project.
   */
  unarchive(): void {
    this.isArchived = false;
    this.updatedAt = new Date();
  }

  /**
   * Get the total number of tasks.
   */
  get taskCount(): number {
    return this._tasks.length;
  }

  /**
   * Get the number of completed tasks.
   */
  get completedTaskCount(): number {
    return this._tasks.filter((t) => t.status === TaskStatus.COMPLETED).length;
  }

  /**
   * Calculate completion percentage.
   *
   * @returns Percentage of completed tasks (0-100)
   */
  get completionPercentage(): number {
    if (this._tasks.length === 0) {
      return 0;
    }
    return (this.completedTaskCount / this.taskCount) * 100;
  }

  /**
   * Check if the project has any overdue tasks.
   */
  get hasOverdueTasks(): boolean {
    return this._tasks.some((t) => t.isOverdue);
  }

  /**
   * Get a summary of the project status.
   *
   * @returns Dictionary with project statistics
   */
  getSummary(): ProjectSummary {
    const statusCounts: Record<string, number> = {};
    for (const task of this._tasks) {
      const statusName = task.status;
      statusCounts[statusName] = (statusCounts[statusName] || 0) + 1;
    }

    return {
      id: this.id,
      name: this.name,
      totalTasks: this.taskCount,
      completedTasks: this.completedTaskCount,
      completionPercentage: this.completionPercentage,
      statusBreakdown: statusCounts,
      hasOverdue: this.hasOverdueTasks,
      memberCount: this.memberIds.length + 1,
    };
  }

  /**
   * Convert project to a plain object.
   */
  toJSON(): IProject {
    return {
      id: this.id,
      name: this.name,
      description: this.description,
      ownerId: this.ownerId,
      memberIds: [...this.memberIds],
      createdAt: this.createdAt,
      updatedAt: this.updatedAt,
      isArchived: this.isArchived,
    };
  }
}
