// Package handlers provides HTTP handlers for the TaskTracker API.
package handlers

import (
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"sync"

	"github.com/example/tasktracker/pkg/models"
)

// TaskStore defines the interface for task storage.
type TaskStore interface {
	// Get retrieves a task by ID.
	Get(ctx context.Context, id string) (*models.Task, error)
	// GetAll retrieves all tasks.
	GetAll(ctx context.Context) ([]*models.Task, error)
	// Create stores a new task.
	Create(ctx context.Context, task *models.Task) error
	// Update updates an existing task.
	Update(ctx context.Context, task *models.Task) error
	// Delete removes a task by ID.
	Delete(ctx context.Context, id string) error
}

// ErrTaskNotFound is returned when a task is not found.
var ErrTaskNotFound = errors.New("task not found")

// InMemoryTaskStore is an in-memory implementation of TaskStore.
type InMemoryTaskStore struct {
	mu    sync.RWMutex
	tasks map[string]*models.Task
}

// NewInMemoryTaskStore creates a new in-memory task store.
func NewInMemoryTaskStore() *InMemoryTaskStore {
	return &InMemoryTaskStore{
		tasks: make(map[string]*models.Task),
	}
}

// Get retrieves a task by ID.
func (s *InMemoryTaskStore) Get(ctx context.Context, id string) (*models.Task, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()

	task, ok := s.tasks[id]
	if !ok {
		return nil, ErrTaskNotFound
	}
	return task, nil
}

// GetAll retrieves all tasks.
func (s *InMemoryTaskStore) GetAll(ctx context.Context) ([]*models.Task, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()

	tasks := make([]*models.Task, 0, len(s.tasks))
	for _, task := range s.tasks {
		tasks = append(tasks, task)
	}
	return tasks, nil
}

// Create stores a new task.
func (s *InMemoryTaskStore) Create(ctx context.Context, task *models.Task) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	s.tasks[task.ID] = task
	return nil
}

// Update updates an existing task.
func (s *InMemoryTaskStore) Update(ctx context.Context, task *models.Task) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	if _, ok := s.tasks[task.ID]; !ok {
		return ErrTaskNotFound
	}
	s.tasks[task.ID] = task
	return nil
}

// Delete removes a task by ID.
func (s *InMemoryTaskStore) Delete(ctx context.Context, id string) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	if _, ok := s.tasks[id]; !ok {
		return ErrTaskNotFound
	}
	delete(s.tasks, id)
	return nil
}

// TaskHandler handles HTTP requests for tasks.
type TaskHandler struct {
	store TaskStore
}

// NewTaskHandler creates a new task handler.
func NewTaskHandler(store TaskStore) *TaskHandler {
	return &TaskHandler{store: store}
}

// CreateTaskRequest is the request body for creating a task.
type CreateTaskRequest struct {
	Title       string `json:"title"`
	ProjectID   string `json:"project_id"`
	Description string `json:"description,omitempty"`
	Priority    int    `json:"priority,omitempty"`
}

// TaskResponse is the response body for a task.
type TaskResponse struct {
	ID          string              `json:"id"`
	Title       string              `json:"title"`
	Description string              `json:"description"`
	ProjectID   string              `json:"project_id"`
	Status      models.TaskStatus   `json:"status"`
	Priority    models.TaskPriority `json:"priority"`
	CreatedAt   string              `json:"created_at"`
	UpdatedAt   string              `json:"updated_at"`
}

// toResponse converts a Task to a TaskResponse.
func toResponse(task *models.Task) *TaskResponse {
	return &TaskResponse{
		ID:          task.ID,
		Title:       task.Title,
		Description: task.Description,
		ProjectID:   task.ProjectID,
		Status:      task.Status,
		Priority:    task.Priority,
		CreatedAt:   task.CreatedAt.Format("2006-01-02T15:04:05Z"),
		UpdatedAt:   task.UpdatedAt.Format("2006-01-02T15:04:05Z"),
	}
}

// Create handles POST /tasks requests.
func (h *TaskHandler) Create(w http.ResponseWriter, r *http.Request) {
	var req CreateTaskRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "invalid request body", http.StatusBadRequest)
		return
	}

	if req.Title == "" {
		http.Error(w, "title is required", http.StatusBadRequest)
		return
	}

	if req.ProjectID == "" {
		http.Error(w, "project_id is required", http.StatusBadRequest)
		return
	}

	task := models.NewTask(req.Title, req.ProjectID)
	if req.Description != "" {
		task.Description = req.Description
	}
	if req.Priority > 0 {
		task.Priority = models.TaskPriority(req.Priority)
	}

	if err := h.store.Create(r.Context(), task); err != nil {
		http.Error(w, "failed to create task", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)
	json.NewEncoder(w).Encode(toResponse(task))
}

// Get handles GET /tasks/{id} requests.
func (h *TaskHandler) Get(w http.ResponseWriter, r *http.Request, id string) {
	task, err := h.store.Get(r.Context(), id)
	if err != nil {
		if errors.Is(err, ErrTaskNotFound) {
			http.Error(w, "task not found", http.StatusNotFound)
			return
		}
		http.Error(w, "failed to get task", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(toResponse(task))
}

// List handles GET /tasks requests.
func (h *TaskHandler) List(w http.ResponseWriter, r *http.Request) {
	tasks, err := h.store.GetAll(r.Context())
	if err != nil {
		http.Error(w, "failed to list tasks", http.StatusInternalServerError)
		return
	}

	responses := make([]*TaskResponse, len(tasks))
	for i, task := range tasks {
		responses[i] = toResponse(task)
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(responses)
}

// Complete handles POST /tasks/{id}/complete requests.
func (h *TaskHandler) Complete(w http.ResponseWriter, r *http.Request, id string) {
	task, err := h.store.Get(r.Context(), id)
	if err != nil {
		if errors.Is(err, ErrTaskNotFound) {
			http.Error(w, "task not found", http.StatusNotFound)
			return
		}
		http.Error(w, "failed to get task", http.StatusInternalServerError)
		return
	}

	task.MarkComplete()

	if err := h.store.Update(r.Context(), task); err != nil {
		http.Error(w, "failed to update task", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(toResponse(task))
}

// Delete handles DELETE /tasks/{id} requests.
func (h *TaskHandler) Delete(w http.ResponseWriter, r *http.Request, id string) {
	if err := h.store.Delete(r.Context(), id); err != nil {
		if errors.Is(err, ErrTaskNotFound) {
			http.Error(w, "task not found", http.StatusNotFound)
			return
		}
		http.Error(w, "failed to delete task", http.StatusInternalServerError)
		return
	}

	w.WriteHeader(http.StatusNoContent)
}
