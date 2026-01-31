// Package models provides data models for the TaskTracker application.
package models

import (
	"errors"
	"regexp"
	"time"

	"github.com/google/uuid"
)

// UserRole represents the role of a user for access control.
type UserRole string

const (
	// UserRoleViewer can only view content.
	UserRoleViewer UserRole = "viewer"
	// UserRoleMember can view and edit content.
	UserRoleMember UserRole = "member"
	// UserRoleAdmin can manage users and content.
	UserRoleAdmin UserRole = "admin"
	// UserRoleOwner has full access to everything.
	UserRoleOwner UserRole = "owner"
)

var (
	emailRegex    = regexp.MustCompile(`^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$`)
	usernameRegex = regexp.MustCompile(`^[a-zA-Z][a-zA-Z0-9_]{2,29}$`)
)

// ErrInvalidEmail is returned when an email address is invalid.
var ErrInvalidEmail = errors.New("invalid email format")

// ErrInvalidUsername is returned when a username is invalid.
var ErrInvalidUsername = errors.New("invalid username format")

// User represents a user in the system.
//
// Users can be assigned to tasks and projects. They have roles
// that determine their access level.
type User struct {
	ID          string     `json:"id"`
	Username    string     `json:"username"`
	Email       string     `json:"email"`
	DisplayName string     `json:"display_name"`
	Role        UserRole   `json:"role"`
	IsActive    bool       `json:"is_active"`
	CreatedAt   time.Time  `json:"created_at"`
	LastLogin   *time.Time `json:"last_login,omitempty"`
}

// NewUser creates a new user with the given username and email.
//
// Returns an error if the username or email is invalid.
func NewUser(username, email string) (*User, error) {
	if !ValidateUsername(username) {
		return nil, ErrInvalidUsername
	}
	if !ValidateEmail(email) {
		return nil, ErrInvalidEmail
	}

	now := time.Now()
	return &User{
		ID:          uuid.New().String(),
		Username:    username,
		Email:       email,
		DisplayName: username,
		Role:        UserRoleMember,
		IsActive:    true,
		CreatedAt:   now,
	}, nil
}

// ValidateEmail checks if an email address is valid.
func ValidateEmail(email string) bool {
	return emailRegex.MatchString(email)
}

// ValidateUsername checks if a username is valid.
func ValidateUsername(username string) bool {
	return usernameRegex.MatchString(username)
}

// HasPermission checks if the user has a specific permission.
func (u *User) HasPermission(permission string) bool {
	permissions := map[UserRole]map[string]bool{
		UserRoleViewer: {"read": true},
		UserRoleMember: {"read": true, "write": true, "comment": true},
		UserRoleAdmin:  {"read": true, "write": true, "comment": true, "manage": true},
		UserRoleOwner:  {"read": true, "write": true, "comment": true, "manage": true, "delete": true},
	}

	rolePerms, ok := permissions[u.Role]
	if !ok {
		return false
	}
	return rolePerms[permission]
}

// PromoteTo promotes the user to a higher role.
//
// Returns true if promotion was successful, false if the new role
// is not higher than the current role.
func (u *User) PromoteTo(newRole UserRole) bool {
	roleHierarchy := map[UserRole]int{
		UserRoleViewer: 0,
		UserRoleMember: 1,
		UserRoleAdmin:  2,
		UserRoleOwner:  3,
	}

	currentLevel := roleHierarchy[u.Role]
	newLevel := roleHierarchy[newRole]

	if newLevel > currentLevel {
		u.Role = newRole
		return true
	}
	return false
}

// Deactivate deactivates the user account.
func (u *User) Deactivate() {
	u.IsActive = false
}

// RecordLogin records a login event.
func (u *User) RecordLogin() {
	now := time.Now()
	u.LastLogin = &now
}

// IsAdmin checks if the user is an admin or owner.
func (u *User) IsAdmin() bool {
	return u.Role == UserRoleAdmin || u.Role == UserRoleOwner
}

// CreateGuest creates a guest user with limited access.
func CreateGuest(displayName string) *User {
	if displayName == "" {
		displayName = "Guest"
	}

	id := uuid.New().String()[:8]
	now := time.Now()

	return &User{
		ID:          uuid.New().String(),
		Username:    "guest_" + id,
		Email:       "guest_" + id + "@example.com",
		DisplayName: displayName,
		Role:        UserRoleViewer,
		IsActive:    true,
		CreatedAt:   now,
	}
}

// UserOption is a function that configures a User.
type UserOption func(*User)

// WithDisplayName sets the user's display name.
func WithDisplayName(name string) UserOption {
	return func(u *User) {
		u.DisplayName = name
	}
}

// WithRole sets the user's role.
func WithRole(role UserRole) UserOption {
	return func(u *User) {
		u.Role = role
	}
}

// NewUserWithOptions creates a new user with optional configurations.
//
// Returns an error if the username or email is invalid.
func NewUserWithOptions(username, email string, opts ...UserOption) (*User, error) {
	user, err := NewUser(username, email)
	if err != nil {
		return nil, err
	}

	for _, opt := range opts {
		opt(user)
	}

	return user, nil
}
