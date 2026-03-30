# AGENTS.md - Guidelines for AI Agents

This file provides guidelines for AI agents operating in this repository.

## Project Overview

**Rating Service** - A Bayesian rating system with open/closed rating mapping for mixtura ranker. Uses FastStream (RabbitMQ), SQLAlchemy (async), PostgreSQL, and Redis.

## Build, Lint, and Test Commands

### Running Tests

```bash
# Run all tests
uv run pytest tests/

# Run specific test directory
uv run pytest tests/domain/service/
uv run pytest tests/infra/postgre/

# Run specific test file
uv run pytest tests/domain/service/test_rating_service.py

# Run single test
uv run pytest tests/domain/service/test_rating_service.py::TestRatingService::test_name

# Run tests matching pattern
uv run pytest -k "test_member"

# Run with verbose output
uv run pytest tests/ -v
```

### Code Quality

This project does not have formal linting configured. Run tests to verify code correctness.

## Code Style Guidelines

### General Principles

- **Architecture**: Anemic domain model - data in models, business logic in services
- **Async**: Use async/await for all I/O operations (database, HTTP, Redis)

### Imports

- Use **absolute imports** with `src.` prefix
- Group imports: stdlib → third-party → local
- Sort alphabetically within groups

```python
# Correct
from datetime import datetime
from uuid import UUID

import pytest

from src.domain.models.rating import RatingSystemConfig
from src.domain.service.rating_math_ops import RatingMathOperations
```

### Naming Conventions

- **Files**: snake_case (`rating_service.py`, `test_rating_service.py`)
- **Classes**: PascalCase (`RatingService`, `HiddenRating`)
- **Functions/methods**: snake_case (`calculate_effective_ratings`)
- **Constants**: UPPER_SNAKE_CASE
- **Private methods**: prefix with underscore (`_get_hidden_rating`)

### Types

- Use Python 3.13+ type hints
- Use `X | None` instead of `Optional[X]`
- Use explicit types for function signatures

```python
async def calculate_effective_ratings(
    self,
    request: EffectiveRatingRequest
) -> EffectiveRatingResponse:
```

### Docstrings

Use concise docstrings in English. Only add docstrings when they provide useful context that cannot be inferred from the method name and signature.

```python
def method_name(param: str) -> bool:
    """Short description of what the method does."""
```

### Error Handling

- Use custom exceptions from `src.domain.exceptions`
- Catch specific exceptions, not broad `Exception`
- Let exceptions propagate up when appropriate

### Project Structure

```
src/
├── domain/           # Domain layer
│   ├── models/       # Data models (Pydantic)
│   ├── service/      # Business logic
│   └── api/          # API handlers
├── infra/            # Infrastructure layer
│   └── postgre/      # PostgreSQL repositories
│       └── repo/     # Repository implementations
tests/
├── conftest.py       # Shared fixtures
├── domain/
│   └── service/      # Service tests
└── infra/
    └── postgre/      # Repository tests
```

### Test Guidelines

**Key principles:**
1. Use `async_session` fixture with automatic rollback
2. Use `factory` fixture for creating test data
3. Follow AAA pattern: Arrange → Act → Assert
4. Test naming: `test_<method>_<description>`
5. Use `@pytest.mark.asyncio(loop_scope="session")` for async tests

**Test fixtures (from conftest.py):**
- `postgres_container` - PostgreSQL testcontainer
- `async_engine` - SQLAlchemy async engine
- `async_session` - Session with rollback
- `factory` - Factory class for test data
- `helpers` - Helper utilities

### Database

- Use SQLAlchemy 2.0 with asyncpg driver
- Use testcontainers for integration tests
- Models inherit from `src.infra.postgre.engine.Base`
- Use `async_sessionmaker` for session factory

### Dependencies

Key dependencies:
- `faststream[rabbit]` - Message queue
- `sqlalchemy>=2.0` - ORM
- `asyncpg` - PostgreSQL async driver
- `pydantic` - Data validation
- `openskill` - Rating calculations
- `pytest-asyncio` - Async test support
- `testcontainers` - Database containers for tests
