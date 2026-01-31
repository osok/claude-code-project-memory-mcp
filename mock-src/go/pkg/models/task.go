// Package models provides data models for the TaskTracker application.
package models

import (
	"strings"
	"time"

	"github.com/google/uuid"
)

// TaskStatus represents the status of a task.
type TaskStatus string

const (
	// TaskStatusPending indicates the task has not been started.
	TaskStatusPending TaskStatus = "pending"
	// TaskStatusInProgress indicates the task is currently being worked on.
	TaskStatusInProgress TaskStatus = "in_progress"
	// TaskStatusBlocked indicates the task is blocked by something.
	TaskStatusBlocked TaskStatus = "blocked"
	// TaskStatusCompleted indicates the task has been completed.
	TaskStatusCompleted TaskStatus = "completed"
	// TaskStatusCancelled indicates the task has been cancelled.
	TaskStatusCancelled TaskStatus = "cancelled"
)

// TaskPriority represents the priority level of a task.
type TaskPriority int

const (
	// TaskPriorityLow indicates a low priority task.
	TaskPriorityLow TaskPriority = 1
	// TaskPriorityMedium indicates a medium priority task.
	TaskPriorityMedium TaskPriority = 2
	// TaskPriorityHigh indicates a high priority task.
	TaskPriorityHigh TaskPriority = 3
	// TaskPriorityCritical indicates a critical priority task.
	TaskPriorityCritical TaskPriority = 4
)

// Task represents a task in the system.
//
// A task belongs to a project and can be assigned to a user.
// Tasks have status and priority tracking with timestamps.
type Task struct {
	ID          string       `json:"id"`
	Title       string       `json:"title"`
	Description string       `json:"description"`
	ProjectID   string       `json:"project_id"`
	AssigneeID  *string      `json:"assignee_id,omitempty"`
	Status      TaskStatus   `json:"status"`
	Priority    TaskPriority `json:"priority"`
	CreatedAt   time.Time    `json:"created_at"`
	UpdatedAt   time.Time    `json:"updated_at"`
	DueDate     *time.Time   `json:"due_date,omitempty"`
	Tags        []string     `json:"tags"`
}

// NewTask creates a new task with the given title and project ID.
//
// The task is initialized with pending status, medium priority,
// and current timestamps.
func NewTask(title, projectID string) *Task {
	now := time.Now()
	return &Task{
		ID:        uuid.New().String(),
		Title:     title,
		ProjectID: projectID,
		Status:    TaskStatusPending,
		Priority:  TaskPriorityMedium,
		CreatedAt: now,
		UpdatedAt: now,
		Tags:      make([]string, 0),
	}
}

// MarkComplete marks the task as completed and updates the timestamp.
func (t *Task) MarkComplete() {
	t.Status = TaskStatusCompleted
	t.UpdatedAt = time.Now()
}

// MarkBlocked marks the task as blocked with an optional reason.
func (t *Task) MarkBlocked(reason string) {
	t.Status = TaskStatusBlocked
	t.UpdatedAt = time.Now()
	if reason != "" {
		t.Description = t.Description + "\n\nBlocked: " + reason
	}
}

// AssignTo assigns the task to a user.
func (t *Task) AssignTo(userID string) {
	t.AssigneeID = &userID
	t.UpdatedAt = time.Now()
}

// AddTag adds a tag to the task.
//
// Returns true if the tag was added, false if it already exists.
func (t *Task) AddTag(tag string) bool {
	normalizedTag := strings.ToLower(strings.TrimSpace(tag))
	for _, existing := range t.Tags {
		if existing == normalizedTag {
			return false
		}
	}
	t.Tags = append(t.Tags, normalizedTag)
	t.UpdatedAt = time.Now()
	return true
}

// RemoveTag removes a tag from the task.
//
// Returns true if the tag was removed, false if not found.
func (t *Task) RemoveTag(tag string) bool {
	normalizedTag := strings.ToLower(strings.TrimSpace(tag))
	for i, existing := range t.Tags {
		if existing == normalizedTag {
			t.Tags = append(t.Tags[:i], t.Tags[i+1:]...)
			t.UpdatedAt = time.Now()
			return true
		}
	}
	return false
}

// IsOverdue checks if the task is past its due date.
func (t *Task) IsOverdue() bool {
	if t.DueDate == nil {
		return false
	}
	return time.Now().After(*t.DueDate) && t.Status != TaskStatusCompleted
}

// IsActive checks if the task is in an active state.
func (t *Task) IsActive() bool {
	return t.Status == TaskStatusPending || t.Status == TaskStatusInProgress
}

// TaskOption is a function that configures a Task.
type TaskOption func(*Task)

// WithDescription sets the task description.
func WithDescription(description string) TaskOption {
	return func(t *Task) {
		t.Description = description
	}
}

// WithAssignee sets the task assignee.
func WithAssignee(userID string) TaskOption {
	return func(t *Task) {
		t.AssigneeID = &userID
	}
}

// WithPriority sets the task priority.
func WithPriority(priority TaskPriority) TaskOption {
	return func(t *Task) {
		t.Priority = priority
	}
}

// WithDueDate sets the task due date.
func WithDueDate(dueDate time.Time) TaskOption {
	return func(t *Task) {
		t.DueDate = &dueDate
	}
}

// WithTags sets the task tags.
func WithTags(tags []string) TaskOption {
	return func(t *Task) {
		t.Tags = make([]string, len(tags))
		for i, tag := range tags {
			t.Tags[i] = strings.ToLower(strings.TrimSpace(tag))
		}
	}
}

// NewTaskWithOptions creates a new task with optional configurations.
func NewTaskWithOptions(title, projectID string, opts ...TaskOption) *Task {
	task := NewTask(title, projectID)
	for _, opt := range opts {
		opt(task)
	}
	return task
}
