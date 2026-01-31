/**
 * Task service for managing tasks.
 */

import { Task, TaskStatus, TaskPriority, ITask } from '../models/Task';
import { validateTaskTitle } from '../utils/validators';

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
 * Options for creating a task.
 */
export interface CreateTaskOptions {
  description?: string;
  assigneeId?: string;
  priority?: TaskPriority;
  dueDate?: Date;
  tags?: string[];
}

/**
 * Options for updating a task.
 */
export interface UpdateTaskOptions {
  title?: string;
  description?: string;
  status?: TaskStatus;
  priority?: TaskPriority;
  assigneeId?: string;
  dueDate?: Date;
}

/**
 * Service for task management operations.
 *
 * Handles business logic for creating, updating, and querying tasks.
 */
export class TaskService {
  private tasks: Map<string, Task> = new Map();
  private cache: Map<string, Task> = new Map();

  /**
   * Create a new task.
   *
   * @param title - Task title
   * @param projectId - ID of the project the task belongs to
   * @param options - Additional task options
   * @returns The created task
   * @throws ValidationError if title is invalid
   */
  createTask(
    title: string,
    projectId: string,
    options: CreateTaskOptions = {}
  ): Task {
    const validation = validateTaskTitle(title);
    if (!validation.isValid) {
      throw new ValidationError('title', validation.errorMessage!);
    }

    const task = new Task(title, projectId, {
      description: options.description,
      assigneeId: options.assigneeId,
      priority: options.priority,
      dueDate: options.dueDate,
      tags: options.tags,
    });

    this.tasks.set(task.id, task);
    return task;
  }

  /**
   * Get a task by ID.
   *
   * @param taskId - The task's unique identifier
   * @returns The task
   * @throws NotFoundError if task doesn't exist
   */
  getTask(taskId: string): Task {
    const task = this.tasks.get(taskId);
    if (!task) {
      throw new NotFoundError('Task', taskId);
    }
    return task;
  }

  /**
   * Update a task's properties.
   *
   * @param taskId - The task to update
   * @param options - Properties to update
   * @returns The updated task
   * @throws NotFoundError if task doesn't exist
   * @throws ValidationError if new values are invalid
   */
  updateTask(taskId: string, options: UpdateTaskOptions): Task {
    const task = this.getTask(taskId);

    if (options.title !== undefined) {
      const validation = validateTaskTitle(options.title);
      if (!validation.isValid) {
        throw new ValidationError('title', validation.errorMessage!);
      }
      task.title = options.title;
    }

    if (options.description !== undefined) {
      task.description = options.description;
    }

    if (options.status !== undefined) {
      task.status = options.status;
    }

    if (options.priority !== undefined) {
      task.priority = options.priority;
    }

    if (options.assigneeId !== undefined) {
      task.assigneeId = options.assigneeId;
    }

    if (options.dueDate !== undefined) {
      task.dueDate = options.dueDate;
    }

    task.updatedAt = new Date();
    this.invalidateCache(taskId);
    return task;
  }

  /**
   * Delete a task.
   *
   * @param taskId - The task to delete
   * @returns True if deleted
   * @throws NotFoundError if task doesn't exist
   */
  deleteTask(taskId: string): boolean {
    if (!this.tasks.has(taskId)) {
      throw new NotFoundError('Task', taskId);
    }

    this.tasks.delete(taskId);
    this.invalidateCache(taskId);
    return true;
  }

  /**
   * Create a task asynchronously.
   *
   * @param title - Task title
   * @param projectId - Project ID
   * @param options - Additional task options
   * @returns Promise resolving to the created task
   */
  async createTaskAsync(
    title: string,
    projectId: string,
    options: CreateTaskOptions = {}
  ): Promise<Task> {
    await new Promise((resolve) => setTimeout(resolve, 10));
    return this.createTask(title, projectId, options);
  }

  /**
   * Create multiple tasks asynchronously.
   *
   * @param tasksData - List of task data
   * @returns Promise resolving to list of created tasks
   */
  async bulkCreateAsync(
    tasksData: Array<{ title: string; projectId: string } & CreateTaskOptions>
  ): Promise<Task[]> {
    const tasks: Task[] = [];
    for (const data of tasksData) {
      const task = await this.createTaskAsync(
        data.title,
        data.projectId,
        data
      );
      tasks.push(task);
    }
    return tasks;
  }

  /**
   * Assign a task to a user.
   *
   * @param taskId - The task to assign
   * @param userId - The user to assign to
   * @returns The updated task
   */
  assignTask(taskId: string, userId: string): Task {
    const task = this.getTask(taskId);
    task.assignTo(userId);
    return task;
  }

  /**
   * Mark a task as completed.
   *
   * @param taskId - The task to complete
   * @returns The updated task
   */
  completeTask(taskId: string): Task {
    const task = this.getTask(taskId);
    task.markComplete();
    return task;
  }

  /**
   * Get all tasks for a specific project.
   *
   * @param projectId - The project ID to filter by
   * @returns List of tasks belonging to the project
   */
  getTasksByProject(projectId: string): Task[] {
    return Array.from(this.tasks.values()).filter(
      (t) => t.projectId === projectId
    );
  }

  /**
   * Get all tasks assigned to a specific user.
   *
   * @param userId - The user ID to filter by
   * @returns List of tasks assigned to the user
   */
  getTasksByAssignee(userId: string): Task[] {
    return Array.from(this.tasks.values()).filter(
      (t) => t.assigneeId === userId
    );
  }

  /**
   * Get all tasks with a specific status.
   *
   * @param status - The status to filter by
   * @returns List of tasks with the given status
   */
  getTasksByStatus(status: TaskStatus): Task[] {
    return Array.from(this.tasks.values()).filter((t) => t.status === status);
  }

  /**
   * Get all overdue tasks.
   *
   * @returns List of tasks past their due date
   */
  getOverdueTasks(): Task[] {
    return Array.from(this.tasks.values()).filter((t) => t.isOverdue);
  }

  /**
   * Search tasks with filters.
   *
   * @param query - Search text
   * @param projectId - Optional project filter
   * @param status - Optional status filter
   * @returns Matching tasks
   */
  searchTasks(
    query: string,
    projectId?: string,
    status?: TaskStatus
  ): Task[] {
    const queryLower = query.toLowerCase();

    return Array.from(this.tasks.values()).filter((task) => {
      const matchesQuery =
        task.title.toLowerCase().includes(queryLower) ||
        task.description.toLowerCase().includes(queryLower);

      if (!matchesQuery) return false;
      if (projectId && task.projectId !== projectId) return false;
      if (status && task.status !== status) return false;

      return true;
    });
  }

  /**
   * Get total number of tasks.
   */
  get taskCount(): number {
    return this.tasks.size;
  }

  /**
   * Calculate a priority score for sorting.
   *
   * @param task - The task to score
   * @returns Priority score (higher = more important)
   */
  static calculatePriorityScore(task: Task): number {
    let score = task.priority * 10;

    if (task.isOverdue) {
      score += 50;
    }

    if (task.status === TaskStatus.BLOCKED) {
      score -= 20;
    }

    return score;
  }

  private invalidateCache(taskId: string): void {
    this.cache.delete(taskId);
  }
}
