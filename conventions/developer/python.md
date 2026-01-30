# Python Conventions

## Project Structure

```
project/
├── src/
│   └── {package_name}/
│       ├── __init__.py
│       ├── main.py           # Entry point
│       ├── config.py         # Configuration
│       ├── models/           # Data models
│       ├── services/         # Business logic
│       ├── api/              # API routes (FastAPI/Flask)
│       └── utils/            # Utilities
├── tests/
│   ├── __init__.py
│   ├── conftest.py           # Pytest fixtures
│   ├── unit/
│   └── integration/
├── scripts/                  # CLI scripts
├── pyproject.toml
├── requirements.txt
└── .env.example
```

## Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Module | snake_case | `user_service.py` |
| Class | PascalCase | `UserService` |
| Function | snake_case | `get_user_by_id` |
| Variable | snake_case | `user_count` |
| Constant | SCREAMING_SNAKE_CASE | `MAX_CONNECTIONS` |
| Private | Leading underscore | `_internal_method` |
| Type alias | PascalCase | `UserId = str` |

## Approved Libraries

| Purpose | Library | Notes |
|---------|---------|-------|
| Web framework | FastAPI or Flask | FastAPI preferred for new projects |
| ORM | SQLAlchemy | With Alembic for migrations |
| Validation | Pydantic | Built into FastAPI |
| HTTP client | httpx | Async support |
| Testing | pytest | With pytest-asyncio for async |
| Linting | Ruff | Fast, replaces flake8/isort/black |
| Type checking | mypy | Strict mode |
| Env config | python-dotenv | Load .env files |
| Logging | structlog | Structured logging |
| CLI | Typer or Click | Typer preferred |

## Build Commands

| Action | Command |
|--------|---------|
| Run | `python -m src.{package}.main` |
| Test | `pytest` |
| Test with coverage | `pytest --cov=src` |
| Lint | `ruff check .` |
| Format | `ruff format .` |
| Type check | `mypy src/` |
| Install deps | `pip install -r requirements.txt` |
| Install dev | `pip install -e ".[dev]"` |

## Code Style

- Follow PEP 8
- Use type hints everywhere
- Prefer f-strings over .format()
- Use pathlib over os.path
- Use dataclasses or Pydantic for data structures
- Keep functions under 30 lines
- Document public APIs with docstrings (Google style)

## Docstring Format (Google Style)

```python
def function(arg1: str, arg2: int) -> bool:
    """Short description.

    Longer description if needed.

    Args:
        arg1: Description of arg1.
        arg2: Description of arg2.

    Returns:
        Description of return value.

    Raises:
        ValueError: When arg2 is negative.
    """
```

## Error Handling

```python
# Custom exceptions
class ServiceError(Exception):
    """Base exception for service errors."""

class NotFoundError(ServiceError):
    """Resource not found."""

# Usage
def get_user(user_id: str) -> User:
    user = db.get(user_id)
    if not user:
        raise NotFoundError(f"User {user_id} not found")
    return user
```
