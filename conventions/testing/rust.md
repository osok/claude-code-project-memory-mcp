# Rust Testing Conventions

## Test Structure

```
project/
├── src/
│   └── user/
│       ├── mod.rs
│       └── service.rs    # Contains #[cfg(test)] module
├── tests/                # Integration tests
│   ├── common/
│   │   └── mod.rs        # Shared test utilities
│   └── user_api_test.rs
└── benches/
    └── user_bench.rs
```

## Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Test module | `tests` | `#[cfg(test)] mod tests` |
| Test function | `test_{scenario}` | `fn test_create_user_valid_input()` |
| Integration test | `{feature}_test.rs` | `user_api_test.rs` |
| Benchmark | `bench_{operation}` | `fn bench_hash_password()` |

## Test Framework

| Purpose | Tool | Notes |
|---------|------|-------|
| Unit tests | Built-in | `#[test]` attribute |
| Async tests | tokio::test | `#[tokio::test]` |
| Mocking | mockall | Trait-based mocking |
| Property testing | proptest | Generative testing |
| Benchmarks | criterion | Statistical benchmarks |
| Assertions | Built-in | `assert!`, `assert_eq!` |

## Test Commands

| Action | Command |
|--------|---------|
| Run all | `cargo test` |
| Run specific | `cargo test test_name` |
| Run module | `cargo test user::` |
| Run integration | `cargo test --test user_api` |
| Show output | `cargo test -- --nocapture` |
| Run ignored | `cargo test -- --ignored` |
| Benchmark | `cargo bench` |
| Doc tests | `cargo test --doc` |

## Unit Tests

```rust
// src/user/service.rs
pub fn validate_email(email: &str) -> Result<(), ValidationError> {
    if email.contains('@') && email.contains('.') {
        Ok(())
    } else {
        Err(ValidationError::InvalidEmail)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_validate_email_valid() {
        assert!(validate_email("user@example.com").is_ok());
    }

    #[test]
    fn test_validate_email_missing_at() {
        assert!(validate_email("userexample.com").is_err());
    }

    #[test]
    fn test_validate_email_missing_dot() {
        assert!(validate_email("user@example").is_err());
    }

    #[test]
    #[should_panic(expected = "empty email")]
    fn test_validate_email_panics_on_empty() {
        validate_email_strict("").unwrap();
    }
}
```

## Async Tests

```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_fetch_user() {
        let client = TestClient::new().await;
        let user = client.get_user("123").await.unwrap();
        assert_eq!(user.id, "123");
    }

    #[tokio::test]
    async fn test_create_user_timeout() {
        let result = tokio::time::timeout(
            Duration::from_secs(5),
            create_user_slow()
        ).await;
        assert!(result.is_ok());
    }
}
```

## Mocking with mockall

```rust
use mockall::automock;

#[automock]
pub trait UserRepository {
    fn find_by_id(&self, id: &str) -> Result<User, Error>;
}

#[cfg(test)]
mod tests {
    use super::*;
    use mockall::predicate::*;

    #[test]
    fn test_user_service_get_user() {
        let mut mock_repo = MockUserRepository::new();
        mock_repo
            .expect_find_by_id()
            .with(eq("123"))
            .times(1)
            .returning(|_| Ok(User { id: "123".into(), name: "Test".into() }));

        let service = UserService::new(Box::new(mock_repo));
        let user = service.get_user("123").unwrap();

        assert_eq!(user.name, "Test");
    }
}
```

## Integration Tests

```rust
// tests/user_api_test.rs
mod common;

use common::TestApp;

#[tokio::test]
async fn test_create_user_endpoint() {
    let app = TestApp::spawn().await;

    let response = app
        .client
        .post(&format!("{}/users", app.address))
        .json(&serde_json::json!({"name": "Test", "email": "test@example.com"}))
        .send()
        .await
        .unwrap();

    assert_eq!(response.status(), 201);
}
```

## Test Fixtures

```rust
// tests/common/mod.rs
pub struct TestApp {
    pub address: String,
    pub client: reqwest::Client,
    pub db: PgPool,
}

impl TestApp {
    pub async fn spawn() -> Self {
        let db = setup_test_db().await;
        let app = build_app(db.clone());
        let listener = TcpListener::bind("127.0.0.1:0").unwrap();
        let address = format!("http://{}", listener.local_addr().unwrap());

        tokio::spawn(async move {
            axum::serve(listener, app).await.unwrap();
        });

        Self {
            address,
            client: reqwest::Client::new(),
            db,
        }
    }
}
```

## Coverage Target

- Minimum: 70% line coverage
- Use `cargo-tarpaulin` or `llvm-cov` for coverage
- Focus on business logic, skip generated code
