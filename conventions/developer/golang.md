# Go Conventions

## Project Structure

```
project/
├── cmd/
│   └── {app}/
│       └── main.go       # Application entry points
├── internal/
│   ├── {domain}/         # Domain-specific code (not exported)
│   └── pkg/              # Internal shared packages
├── pkg/                  # Exported packages (public API)
├── api/                  # API definitions (OpenAPI, protobuf)
├── configs/              # Configuration files
├── scripts/              # Build/deploy scripts
├── test/                 # Integration test data
└── go.mod
```

## Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Package | lowercase, single word | `user`, `auth` |
| File | lowercase, underscores | `user_service.go` |
| Exported function | PascalCase | `CreateUser` |
| Unexported function | camelCase | `validateInput` |
| Constant | PascalCase or ALL_CAPS | `MaxRetries`, `DEFAULT_TIMEOUT` |
| Interface | -er suffix when possible | `Reader`, `UserService` |
| Struct | PascalCase | `UserRequest` |

## Approved Libraries

| Purpose | Library | Notes |
|---------|---------|-------|
| HTTP router | chi or gin | chi preferred for simplicity |
| Database | sqlx | SQL with struct mapping |
| Logging | zerolog or slog | Structured logging |
| Config | viper | Environment + file config |
| Testing | testify | Assertions and mocks |
| Validation | validator/v10 | Struct tag validation |
| UUID | google/uuid | Standard UUID generation |

## Build Commands

| Action | Command |
|--------|---------|
| Build | `go build -o bin/{app} ./cmd/{app}` |
| Test | `go test ./...` |
| Test with coverage | `go test -coverprofile=coverage.out ./...` |
| Lint | `golangci-lint run` |
| Format | `go fmt ./...` |
| Run | `go run ./cmd/{app}` |
| Tidy deps | `go mod tidy` |

## Error Handling

```go
// Wrap errors with context
if err != nil {
    return fmt.Errorf("failed to create user: %w", err)
}

// Custom error types for domain errors
type NotFoundError struct {
    Resource string
    ID       string
}
```

## Code Style

- Keep functions short (< 50 lines)
- Return early on errors
- Use table-driven tests
- Accept interfaces, return structs
- Document exported functions
