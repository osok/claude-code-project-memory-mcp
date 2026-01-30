# Go Testing Conventions

## Test Structure

```
project/
├── internal/
│   └── user/
│       ├── service.go
│       └── service_test.go    # Unit tests alongside code
├── test/
│   ├── integration/           # Integration tests
│   │   └── user_test.go
│   ├── e2e/                   # End-to-end tests
│   └── fixtures/              # Test data
└── testutil/                  # Shared test utilities
```

## Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Test file | `{file}_test.go` | `service_test.go` |
| Test function | `Test{Function}_{Scenario}` | `TestCreateUser_ValidInput` |
| Benchmark | `Benchmark{Function}` | `BenchmarkHashPassword` |
| Subtest | Descriptive string | `t.Run("returns error for invalid email", ...)` |

## Test Framework

| Purpose | Tool | Import |
|---------|------|--------|
| Assertions | testify/assert | `github.com/stretchr/testify/assert` |
| Mocking | testify/mock | `github.com/stretchr/testify/mock` |
| HTTP testing | httptest | `net/http/httptest` |
| Table tests | Built-in | Native Go |

## Test Commands

| Action | Command |
|--------|---------|
| Run all | `go test ./...` |
| Run specific | `go test ./internal/user/...` |
| Verbose | `go test -v ./...` |
| Coverage | `go test -coverprofile=coverage.out ./...` |
| Coverage HTML | `go tool cover -html=coverage.out` |
| Race detection | `go test -race ./...` |
| Short mode | `go test -short ./...` |
| Benchmark | `go test -bench=. ./...` |

## Table-Driven Tests

```go
func TestValidateEmail(t *testing.T) {
    tests := []struct {
        name    string
        email   string
        wantErr bool
    }{
        {
            name:    "valid email",
            email:   "user@example.com",
            wantErr: false,
        },
        {
            name:    "missing domain",
            email:   "user@",
            wantErr: true,
        },
        {
            name:    "empty string",
            email:   "",
            wantErr: true,
        },
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            err := ValidateEmail(tt.email)
            if tt.wantErr {
                assert.Error(t, err)
            } else {
                assert.NoError(t, err)
            }
        })
    }
}
```

## Mocking

```go
// Define interface
type UserRepository interface {
    FindByID(ctx context.Context, id string) (*User, error)
}

// Generate mock (or use testify/mock)
type MockUserRepository struct {
    mock.Mock
}

func (m *MockUserRepository) FindByID(ctx context.Context, id string) (*User, error) {
    args := m.Called(ctx, id)
    if args.Get(0) == nil {
        return nil, args.Error(1)
    }
    return args.Get(0).(*User), args.Error(1)
}

// Use in test
func TestUserService_GetUser(t *testing.T) {
    mockRepo := new(MockUserRepository)
    service := NewUserService(mockRepo)

    expectedUser := &User{ID: "123", Name: "Test"}
    mockRepo.On("FindByID", mock.Anything, "123").Return(expectedUser, nil)

    user, err := service.GetUser(context.Background(), "123")

    assert.NoError(t, err)
    assert.Equal(t, expectedUser, user)
    mockRepo.AssertExpectations(t)
}
```

## Integration Tests

```go
//go:build integration

package integration

func TestUserAPI_CreateUser(t *testing.T) {
    // Setup test database
    db := setupTestDB(t)
    defer db.Close()

    // Create test server
    srv := httptest.NewServer(setupRouter(db))
    defer srv.Close()

    // Make request
    resp, err := http.Post(srv.URL+"/users", "application/json",
        strings.NewReader(`{"name":"Test"}`))

    assert.NoError(t, err)
    assert.Equal(t, http.StatusCreated, resp.StatusCode)
}
```

## Test Fixtures

```go
// testutil/fixtures.go
func NewTestUser(overrides ...func(*User)) *User {
    user := &User{
        ID:    uuid.NewString(),
        Name:  "Test User",
        Email: "test@example.com",
    }
    for _, override := range overrides {
        override(user)
    }
    return user
}

// Usage
user := NewTestUser(func(u *User) {
    u.Name = "Custom Name"
})
```

## Coverage Target

- Minimum: 70% line coverage
- Focus on business logic, not boilerplate
- Skip generated code from coverage
