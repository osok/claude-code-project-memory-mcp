# Python Testing Conventions

## Test Structure

```
project/
├── src/
│   └── mypackage/
│       ├── services/
│       │   └── user_service.py
│       └── models/
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # Shared fixtures
│   ├── unit/
│   │   ├── __init__.py
│   │   └── services/
│   │       └── test_user_service.py
│   ├── integration/
│   │   ├── __init__.py
│   │   └── test_user_api.py
│   └── fixtures/                # Test data
│       └── users.json
```

## Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Test file | `test_{module}.py` | `test_user_service.py` |
| Test class | `Test{Class}` | `TestUserService` |
| Test function | `test_{method}_{scenario}` | `test_create_user_valid_input` |
| Fixture | snake_case | `db_session`, `test_user` |

## Test Framework

| Purpose | Tool | Notes |
|---------|------|-------|
| Test runner | pytest | With plugins |
| Assertions | pytest (native) | Or pytest-assume |
| Mocking | pytest-mock / unittest.mock | pytest-mock preferred |
| Fixtures | pytest fixtures | Scoped fixtures |
| Async | pytest-asyncio | For async code |
| HTTP mocking | responses / httpx-mock | responses for requests |
| Coverage | pytest-cov | Coverage reporting |

## Test Commands

| Action | Command |
|--------|---------|
| Run all | `pytest` |
| Verbose | `pytest -v` |
| Single file | `pytest tests/unit/test_user.py` |
| Single test | `pytest -k "test_create_user"` |
| Coverage | `pytest --cov=src --cov-report=html` |
| Failed only | `pytest --lf` |
| Parallel | `pytest -n auto` (pytest-xdist) |
| Markers | `pytest -m "not slow"` |

## Basic Test Structure

```python
# tests/unit/services/test_user_service.py
import pytest
from mypackage.services.user_service import UserService
from mypackage.models import User


class TestUserService:
    """Tests for UserService."""

    def test_create_user_valid_input(self, mock_repo):
        """Should create user with valid input."""
        service = UserService(mock_repo)

        user = service.create_user(name="John", email="john@example.com")

        assert user.name == "John"
        assert user.email == "john@example.com"
        mock_repo.save.assert_called_once()

    def test_create_user_invalid_email(self, mock_repo):
        """Should raise ValueError for invalid email."""
        service = UserService(mock_repo)

        with pytest.raises(ValueError, match="Invalid email"):
            service.create_user(name="John", email="invalid")
```

## Fixtures

```python
# tests/conftest.py
import pytest
from unittest.mock import MagicMock, AsyncMock


@pytest.fixture
def mock_repo():
    """Create a mock repository."""
    repo = MagicMock()
    repo.find_by_id.return_value = None
    return repo


@pytest.fixture
def test_user():
    """Create a test user."""
    return User(id="123", name="Test User", email="test@example.com")


@pytest.fixture
async def async_client(app):
    """Create async test client."""
    from httpx import AsyncClient
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture(scope="session")
def db_engine():
    """Create test database engine (session-scoped)."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()
```

## Mocking

```python
from unittest.mock import MagicMock, patch, AsyncMock


def test_service_calls_external_api(mocker):
    """Test with pytest-mock."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"data": "value"}

    mocker.patch("mypackage.services.requests.get", return_value=mock_response)

    result = my_service.fetch_data()

    assert result == {"data": "value"}


# Async mocking
async def test_async_service(mocker):
    """Test async function."""
    mock_fetch = AsyncMock(return_value={"id": "123"})
    mocker.patch("mypackage.services.fetch_user", mock_fetch)

    result = await my_service.get_user("123")

    assert result["id"] == "123"
```

## Parametrized Tests

```python
@pytest.mark.parametrize("email,expected_valid", [
    ("user@example.com", True),
    ("user@domain.co.uk", True),
    ("invalid-email", False),
    ("@nodomain.com", False),
    ("", False),
])
def test_validate_email(email, expected_valid):
    """Test email validation with multiple inputs."""
    result = validate_email(email)
    assert result == expected_valid
```

## Integration Tests

```python
# tests/integration/test_user_api.py
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestUserAPI:
    """Integration tests for User API."""

    async def test_create_user(self, async_client: AsyncClient, db_session):
        """Should create user via API."""
        response = await async_client.post(
            "/users",
            json={"name": "John", "email": "john@example.com"}
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "John"
        assert "id" in data

    async def test_get_user_not_found(self, async_client: AsyncClient):
        """Should return 404 for non-existent user."""
        response = await async_client.get("/users/nonexistent")

        assert response.status_code == 404
```

## Test Markers

```python
# pytest.ini or pyproject.toml
[tool.pytest.ini_options]
markers = [
    "slow: marks tests as slow",
    "integration: marks tests as integration tests",
    "e2e: marks tests as end-to-end tests",
]

# Usage
@pytest.mark.slow
def test_complex_operation():
    ...

@pytest.mark.integration
async def test_database_query():
    ...
```

## Coverage Target

- Minimum: 70% line coverage
- Focus on business logic
- Exclude migrations, configs from coverage
