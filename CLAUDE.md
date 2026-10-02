# CLAUDE.md — my-fastapi

Project file for **my-fastapi**. The sections from "Tooling" to "Testing" mirror the global conventions (`C:\Users\normist\Claude\CLAUDE.md`) — when a general rule changes, update both files. Everything specific to this repository is at the end, under "This project".

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
- `Settings` and `get_settings()` live in `core/config.py`, not next to the DB engine — settings serve more than the database (JWT secret, CORS, ...).

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
  - `Mapped[...]` takes Python types (`Mapped[str]`, `Mapped[datetime]`): never Pydantic types (`Mapped[EmailStr]` fails to map) and never SQL types (`DateTime(timezone=True)` goes inside `mapped_column`). Validation lives in Pydantic schemas; models and repositories don't import Pydantic.
  - `updated_at` needs `onupdate=...`, not just `default=...`.
  - Plain `DeclarativeBase` by default; `MappedAsDataclass` (typed `__init__`, needs `kw_only=True`, `init=False` + `insert_default` for DB-filled fields) only when explicitly wanted.
- **Schemas** — group repeated read-only fields (e.g. `id`, `created_at`, `updated_at`) into small Pydantic mixins kept alongside the schemas that use them (not in the ORM `base.py`); name them plainly (`IDMixin`, `TimestampMixin`), without a "Schema" prefix/suffix, since the module already makes clear they're Pydantic, not ORM.
  - Client-input schemas never carry privilege/status fields: a public sign-up schema (`UserRegister`: email, password, full_name) is separate from the admin-only `UserCreate` (which may set `is_superuser`, `is_active`).
  - Split response schemas by audience: `UserPublic` (safe for other users) vs full `UserRead` (admin). Schemas built from ORM objects include `from_attributes=True` (an `ORMReadMixin`).
  - Mixins already inherit `BaseModel` — don't list `BaseModel` before them in the bases (MRO error); just omit it.

### Conventions inside the layers

- **Naming**: interfaces get the `Abstract` prefix (`AbstractRepository`, `AbstractUnitOfWork`); implementations get a technology prefix (`SQLAlchemyUserRepository`, `SQLAlchemyUnitOfWork`, `FakeUserRepository`).
- **Entity repositories**: add an entity-specific interface (`AbstractUserRepository(AbstractRepository[User])`) as soon as the entity needs its own query (e.g. `get_by_email`), and annotate the UoW attribute with it (`users: AbstractUserRepository`). The concrete UoW instantiates the concrete repositories with its single shared session — that's what makes them one transaction.
- **Repository code**: the generic base uses `self.model` (a class attribute, `model = User`, on each subclass); entity-specific queries use the model directly (`select(User).where(User.email == email)`). Unique lookups → `scalar_one_or_none()`. Parameters are plain Python types (`email: str`).
- **Services**:
  - One public method = one `async with self.uow:` block = one transaction; commit explicitly with `await self.uow.commit()`.
  - Build the response schema (`UserPublic.model_validate(obj)`) inside the block and return Pydantic, never ORM objects. Relationships a response needs are loaded in the repository (`selectinload`) — lazy loading after the session closes fails in async.
  - Build ORM objects from schemas with explicit fields (`User(email=data.email, ...)`), not `**data.model_dump()`, so new schema fields can't leak into the DB.
  - Don't call another service's method inside an open `async with self.uow:` — FastAPI caches `get_uow` per request, so services share one UoW instance, and re-entering it replaces `self.session` (the outer work is silently lost).
- **Domain exceptions**: services raise domain exceptions, never `HTTPException`. Keep them in `services/exceptions.py` as a hierarchy on `Exception` (`DomainError` → `NotFoundError` / `AlreadyExistsError` → `UserNotFound`, ...), pass the relevant data to `super().__init__(message)`, and map them to HTTP codes with `exception_handler`s in `main.py` (or in the router).
- **UoW `__aexit__`**: rollback in `try`, `session.close()` in `finally`, so a failing rollback doesn't leak the connection.
- **Dependencies** (`api/deps.py` — the composition root, lives in the API layer because it's FastAPI-specific): `get_uow()` is a plain function returning `AbstractUnitOfWork` (not a `yield` dependency — commits stay in services); expose `Annotated` aliases (`UoWDep`, `UserServiceDep`); no session dependency for routers. Tests swap implementations via `app.dependency_overrides[get_uow]`.

For tests, prefer an in-memory/fake Unit of Work + repositories for service-level unit tests, and a real UoW against a test database for integration tests.

## Code style

- Type hints everywhere; the codebase should pass `mypy` (and/or `ty`) cleanly.
- `ruff check --fix` + `ruff format` for linting/formatting — via `uv run ruff ...`.
- Prefer `async def` endpoints and async DB access when the project's driver/session setup supports it; don't mix sync and async DB calls in the same path.
- Keep Pydantic schemas and ORM models named distinctly (e.g. `UserCreate`/`UserRead` vs `User`), even if a project happens to use SQLModel's single-class style — call that out as a deviation from this preference if it comes up.
- Type self-returning methods (`__aenter__`, alternative constructors, etc.) with `typing.Self`, not a stringified forward-reference to the class name.
- Every package directory has an `__init__.py` (without them mypy fails on duplicate module names such as two `base.py`).
- Use the most modern syntax the project's `requires-python` allows; new projects target Python 3.14 (`requires-python = ">=3.14"`):
  - PEP 695 generics (3.12+): `class AbstractRepository[ModelT: Base](ABC)`, `def first[T](items: list[T]) -> T`, `type UserId = uuid.UUID` — not module-level `TypeVar(...)` + `Generic[...]`. Concrete subclasses still just substitute the type: `SQLAlchemyRepository[User]`.
  - `X | None` and `A | B` instead of `Optional`/`Union`; built-in generics (`list[int]`, `dict[str, Any]`) instead of `typing.List`/`Dict`.
  - No `from __future__ import annotations` and no quoted forward references (3.14+): 3.14 evaluates annotations lazily (PEP 649), so e.g. `Mapped[list[Item]]` before `Item` is defined works as-is.
  - `ruff` (pyupgrade `UP` rules, target taken from `requires-python`) flags old-style syntax — fix it rather than suppress.

## Testing

- pytest, with fixtures for a test database/session and a fake Unit of Work.
- Fake repositories set `id`, `created_at`, `updated_at` themselves: ORM column defaults are applied only on `flush()`, so without a DB they stay `None` and response-schema validation fails.
- One test module per feature/router; name tests after the behavior, not the function.
- Run the full suite via `uv run pytest` before considering backend work done.

---

# This project

Learning project: FastAPI + async SQLAlchemy with Repository + Unit of Work.

## Layout

- `src/` is the package root (every directory has `__init__.py`); use absolute imports `from src...`.
- `src/core/config.py` — `Settings`.
- `src/core/db/` — `base.py` (`Base` = plain `DeclarativeBase`, ORM `IDMixin` / `TimestampMixin`), `db.py` (`engine`, `async_session_factory`), `models.py` (`User`, `Item`), `schemas.py` (Pydantic schemas + `IDMixin` / `TimestampMixin` / `ORMReadMixin`).
- `src/core/uow.py` — `AbstractUnitOfWork` / `SQLAlchemyUnitOfWork`.
- `src/core/security.py` — password hashing.
- `src/repositories/` — `base.py` (`AbstractRepository`, `SQLAlchemyRepository`), `user.py` (`AbstractUserRepository`, `SQLAlchemyUserRepository`), `item.py` (`SQLAlchemyItemRepository`).
- `src/services/` — `user.py` (`UserService`), `exceptions.py` (domain exceptions).
- `src/api/dep.py` — dependencies (`get_uow`, `UoWDep`, `get_user_service`, `UserServiceDep`); routers in `src/api/v1/routes/`.

## Project decisions

- Python 3.14 (`.python-version`, `requires-python = ">=3.14"`): PEP 695 generics in `repositories/base.py`, no `TypeVar` / `Generic`.
- `Item` exists only together with its `User`: `ForeignKey("user.id", ondelete="CASCADE")` + `cascade="all, delete-orphan"` on `User.items`.
- User schemas: `UserRegister` (public sign-up), `UserCreate` (admin), `UserPublic` (other users), `UserRead` (admin), `UserReadWithItems` (needs `selectinload(User.items)` in the repository).
- Plain `DeclarativeBase`, no `MappedAsDataclass` — deliberate, keep it simple for now.

## Local dev

- `docker compose up -d` — Postgres 18 (`postgres:18`), db `my_fastapi`, port 5432, named volume at `/var/lib/postgresql`.
- `.env`: `POSTGRES_DSN=postgresql+asyncpg://...` (gitignored).

## Status / TODO

Keep this section current.

- `core/security.hash_password` is a stub (returns `None`) — choose a hashing library.
- `get_settings()` is still in `core/db/db.py` — move it next to `Settings` in `core/config.py`.
- `services/exceptions.py` has `NotFoundError` / `AlreadyExistsError` → `UserNotFound` / `UserAlreadyExists`, but no common `DomainError` base and no `exception_handler`s in `main.py` yet.
- `src/main.py`, `src/api/v1/main.py` and the routers are empty; no `ItemService` yet.
- No Alembic, no tests, no `.env.example`; `ruff` / `mypy` / `pytest` aren't dev dependencies yet (`uv add --dev ...`).
