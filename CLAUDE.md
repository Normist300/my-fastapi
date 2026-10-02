# CLAUDE.md

Personal conventions for FastAPI/Python work. Applies across projects, not to one specific repo.

## Tooling

- Package manager is **uv**, never pip/poetry directly.
  - `uv init` — new project
  - `uv add <pkg>` / `uv add --dev <pkg>` — add a runtime/dev dependency (updates `pyproject.toml` + `uv.lock`)
  - `uv sync` — install/lock dependencies
  - `uv run <command>` — run anything inside the project's venv (`uv run fastapi dev`, `uv run pytest`, `uv run alembic upgrade head`, etc.)
- If something about a library or tool looks like it may be outdated (an API, a flag, a recommended pattern), say so and ask whether to check the current docs instead of assuming.

## Stack

FastAPI, Pydantic v2, SQLAlchemy 2.0 (async) + Pydantic (no SQLModel), Alembic for migrations, PostgreSQL, pytest for tests.

## Configuration

- Load settings via `pydantic-settings` (`BaseSettings` + `SettingsConfigDict(env_file=".env", extra="ignore")`); wrap the instance in an `@lru_cache`-decorated `get_settings()` accessor so `.env` is parsed once.
- `.env` holds real secrets and stays gitignored; commit a `.env.example` with the same keys and placeholder values.

## Database (PostgreSQL, async)

- Async driver: `asyncpg` by default (`postgresql+asyncpg://...`). Consider `psycopg` (3.x async) only for API parity with existing sync code or psycopg-specific features (COPY, server-side cursors).
- `create_async_engine(..., pool_pre_ping=True)` to avoid stale pooled connections.
- `async_sessionmaker(engine, expire_on_commit=False)` — required for usable attribute access on ORM objects after `commit()` in async code.
- Local Postgres via Docker Compose (official `postgres` image, named volume for persistence). Note: the data volume path changed with Postgres 18 (`/var/lib/postgresql`, not the older `/var/lib/postgresql/data`) — check the image's docs when bumping the major version.

## Architecture: Repository + Unit of Work

Default to this layering unless a project's existing code already does something else — in that case, follow the existing pattern and flag the mismatch rather than silently introducing a repository layer.

- **Routers** (`api/routes/*.py`) — thin. Parse/validate input via Pydantic, call a service, map the result to a response schema. No direct ORM/session access.
- **Services** — business logic. Depend on the Unit of Work (usually via FastAPI `Depends`), not on repositories or the session directly.
- **Repositories** — one per aggregate/entity, behind an interface (`Protocol` or `ABC`) so they can be swapped for fakes in tests. Own the queries for that entity; no business logic.
- **Unit of Work** — wraps a transaction/session, exposes the repositories it owns, and commits/rolls back as a single unit. Services call `uow.commit()` explicitly; the UoW's `__aexit__` rolls back unconditionally by default (not only on exception) — an explicit `commit()` beforehand makes the subsequent rollback a no-op on the freshly auto-begun transaction.
- **Models** — ORM models (SQLAlchemy/SQLModel) kept separate from the Pydantic request/response schemas; don't return ORM objects straight from a router.
- **Schemas** — group repeated read-only fields (e.g. `id`, `created_at`, `updated_at`) into small Pydantic mixins kept alongside the schemas that use them (not in the ORM `base.py`); name them plainly (`IDMixin`, `TimestampMixin`), without a "Schema" prefix/suffix, since the module already makes clear they're Pydantic, not ORM.

For tests, prefer an in-memory/fake Unit of Work + repositories for service-level unit tests, and a real UoW against a test database for integration tests.

## Code style

- Type hints everywhere; the codebase should pass `mypy` (and/or `ty`) cleanly.
- `ruff check --fix` + `ruff format` for linting/formatting — via `uv run ruff ...`.
- Prefer `async def` endpoints and async DB access when the project's driver/session setup supports it; don't mix sync and async DB calls in the same path.
- Keep Pydantic schemas and ORM models named distinctly (e.g. `UserCreate`/`UserRead` vs `User`), even if a project happens to use SQLModel's single-class style — call that out as a deviation from this preference if it comes up.
- Type self-returning methods (`__aenter__`, alternative constructors, etc.) with `typing.Self`, not a stringified forward-reference to the class name.
- Target Python 3.14 (`requires-python = ">=3.14"`) and use its modern syntax:
  - PEP 695 generics: `class AbstractRepository[ModelT: Base](ABC)`, `def first[T](items: list[T]) -> T`, `type UserId = uuid.UUID` — not module-level `TypeVar(...)` + `Generic[...]`. Concrete subclasses still just substitute the type: `SQLAlchemyRepository[User]`.
  - `X | None` and `A | B` instead of `Optional`/`Union`; built-in generics (`list[int]`, `dict[str, Any]`) instead of `typing.List`/`Dict`.
  - No `from __future__ import annotations` and no quoted forward references: 3.14 evaluates annotations lazily (PEP 649), so e.g. `Mapped[list[Item]]` before `Item` is defined works as-is.
  - `ruff` (pyupgrade `UP` rules, target taken from `requires-python`) flags old-style syntax — fix it rather than suppress.

## Testing

- pytest, with fixtures for a test database/session and a fake Unit of Work.
- One test module per feature/router; name tests after the behavior, not the function.
- Run the full suite via `uv run pytest` before considering backend work done.
