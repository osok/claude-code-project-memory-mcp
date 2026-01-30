# Rust Conventions

## Project Structure

```
project/
├── src/
│   ├── main.rs           # Binary entry point
│   ├── lib.rs            # Library root
│   ├── bin/              # Additional binaries
│   └── {module}/
│       ├── mod.rs        # Module definition
│       └── *.rs          # Module files
├── tests/                # Integration tests
├── benches/              # Benchmarks
├── examples/             # Example code
├── Cargo.toml
└── Cargo.lock
```

## Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Crate | snake_case | `my_crate` |
| Module | snake_case | `user_service` |
| Function | snake_case | `create_user` |
| Struct | PascalCase | `UserRequest` |
| Enum | PascalCase | `Status` |
| Enum variant | PascalCase | `Status::Active` |
| Constant | SCREAMING_SNAKE_CASE | `MAX_CONNECTIONS` |
| Trait | PascalCase | `Serialize` |
| Type parameter | Single uppercase | `T`, `E`, `K`, `V` |

## Approved Libraries

| Purpose | Library | Notes |
|---------|---------|-------|
| Async runtime | tokio | Default async runtime |
| HTTP server | axum or actix-web | axum preferred for simplicity |
| HTTP client | reqwest | Async HTTP client |
| Serialization | serde | With serde_json |
| Database | sqlx | Async SQL with compile-time checks |
| Error handling | thiserror, anyhow | thiserror for libs, anyhow for apps |
| Logging | tracing | Structured logging |
| CLI | clap | Command-line parsing |
| Testing | Built-in + mockall | Native tests + mocking |

## Build Commands

| Action | Command |
|--------|---------|
| Build | `cargo build` |
| Build release | `cargo build --release` |
| Run | `cargo run` |
| Test | `cargo test` |
| Lint | `cargo clippy` |
| Format | `cargo fmt` |
| Check | `cargo check` |
| Doc | `cargo doc --open` |
| Update deps | `cargo update` |

## Error Handling

```rust
// Use thiserror for library errors
#[derive(Debug, thiserror::Error)]
pub enum UserError {
    #[error("user not found: {0}")]
    NotFound(String),
    #[error("invalid email format")]
    InvalidEmail,
    #[error("database error: {0}")]
    Database(#[from] sqlx::Error),
}

// Use Result type alias
pub type Result<T> = std::result::Result<T, UserError>;

// Propagate with ?
fn get_user(id: &str) -> Result<User> {
    let user = db.find_user(id)?;
    Ok(user)
}
```

## Code Style

- Use `rustfmt` defaults
- Prefer `impl Trait` over generics when possible
- Use `#[must_use]` for functions with important return values
- Document public APIs with `///` doc comments
- Use `clippy::pedantic` for stricter lints
- Avoid `unwrap()` in production code; use `expect()` with message or `?`
- Prefer iterators over manual loops
