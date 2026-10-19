# CLAUDE.md — my-fastapi

Project file for **my-fastapi**. The sections from "Tooling" to "Testing" mirror the global conventions (`C:\Users\normist\.claude\CLAUDE.md`) — when a general rule changes, update both files. Everything specific to this repository is at the end, under "This project".

## Tooling

- Package manager is **uv**, never pip/poetry directly.
  - `uv init` — new project
  - `uv add <pkg>` / `uv add --dev <pkg>` — add a runtime/dev dependency (updates `pyproject.toml` + `uv.lock`)
  - `uv sync` — install/lock dependencies
  - `uv run <command>` — run anything inside the project's venv (`uv run fastapi dev`, `uv run pytest`, `uv run alembic upgrade head`, etc.)
  - `uv run fastapi dev` needs `fastapi[standard]`; with plain `fastapi` + `uvicorn` run `uv run uvicorn <module>:app --reload`.
- If something about a library or tool looks like it may be outdated (an API, a flag, a recommended pattern), say so and ask whether to check the current docs instead of assuming.

## Stack

FastAPI, Pydantic v2, SQLAlchemy 2.0 (async) + Pydantic (no SQLModel), Alembic for migrations, PostgreSQL, pytest for tests.

## Configuration

- Load settings via `pydantic-settings` (`BaseSettings` + `SettingsConfigDict(env_file=".env", extra="ignore")`); wrap the instance in an `@lru_cache`-decorated `get_settings()` accessor so `.env` is parsed once.
- `.env` holds real secrets and stays gitignored; commit a `.env.example` with the same keys and placeholder values.
- `Settings` and `get_settings()` live in `core/config.py`, not next to the DB engine — settings serve more than the database (JWT secret, CORS, ...).
- App-level settings (`app_name`, `debug`, `api_v1_prefix`) live in `Settings` with safe defaults; `debug` defaults to `False` (it only turns on tracebacks in 500 responses, which leak paths and secrets) and `DEBUG=true` is set only in a local `.env`.

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
- **Models** — ORM models (SQLAlchemy) kept separate from the Pydantic request/response schemas; don't return ORM objects straight from a router.
  - `Mapped[...]` takes Python types (`Mapped[str]`, `Mapped[datetime]`): never Pydantic types (`Mapped[EmailStr]` fails to map) and never SQL types (`DateTime(timezone=True)` goes inside `mapped_column`). Validation lives in Pydantic schemas; models and repositories don't import Pydantic.
  - `updated_at` needs `onupdate=...`, not just `default=...`. No manual `flush()` for it: `commit()` flushes, and `onupdate` fires only when an `UPDATE` is actually sent (assigning the same values emits nothing, so the timestamp stays).
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
  - Updates: a separate update schema with optional fields (PATCH semantics) and `model_dump(exclude_unset=True)`; apply it with explicit assignments, or a `setattr` loop only over an explicit allow-list of fields (the schema alone must not be the only guard — an `owner_id` added later would become writable). Never let `None` through for non-nullable columns.
  - Repeated "load or raise" goes into a private helper (`async def _get_or_raise(self, id) -> User`, always `await`ed) used inside the `async with self.uow:` block.
  - Deletes: the service loads the object (raising `NotFound`), then calls `repo.delete(obj)`; the repository takes the already-loaded object and never silently no-ops. The second lookup would hit the session's identity map anyway (one session = one `async with self.uow:` block), but passing the object keeps it explicit.
  - Don't call another service's method inside an open `async with self.uow:` — FastAPI caches `get_uow` per request, so services share one UoW instance, and re-entering it replaces `self.session` (the outer work is silently lost).
- **Domain exceptions**: services raise domain exceptions, never `HTTPException`. Keep them in `services/exceptions.py` as a hierarchy on `Exception` (`DomainException` → `NotFoundError` / `AlreadyExistsError` → `UserNotFound`, ...), pass the relevant data to `super().__init__(message)`. Each branch carries its HTTP status as a class attribute (`status_code: ClassVar[int] = status.HTTP_404_NOT_FOUND`, `from fastapi import status` — same constants as in the routers, one style across the project); subclasses inherit it and override only when they need a different code. One `exception_handler` on `DomainException` (registered from `main.py`) builds the response from `exc.status_code` + the message — no separate exception → status mapping table. Deliberate trade-off: strict layer purity isn't a goal here. Register it as `app.exception_handler(DomainException)(domain_exception_handler)` (not `add_exception_handler`: mypy rejects a handler typed `exc: DomainException` there); name unused handler parameters `_` (`_: Request`).
- **App entrypoint** (`main.py`): `FastAPI(title=settings.app_name, debug=settings.debug, lifespan=lifespan)`, one aggregating `api_router` per API version (`api/v1/main.py` includes the entity routers, `main.py` mounts it with `settings.api_v1_prefix`), then the exception handlers. `lifespan` is an `@asynccontextmanager` annotated `-> AsyncGenerator[None]` (not `AsyncIterator`, which is deprecated for this; for `@contextmanager` use `Generator[None]`) that does `await engine.dispose()` after `yield`; tables come from Alembic, not `create_all`.
- **UoW `__aexit__`**: rollback in `try`, `session.close()` in `finally`, so a failing rollback doesn't leak the connection.
- **Dependencies** (`api/deps.py` — the composition root, lives in the API layer because it's FastAPI-specific): `get_uow()` is a plain function returning `AbstractUnitOfWork` (not a `yield` dependency — commits stay in services); expose `Annotated` aliases (`UoWDep`, `UserServiceDep`); no session dependency for routers. Tests swap implementations via `app.dependency_overrides[get_uow]`.

For tests, prefer an in-memory/fake Unit of Work + repositories for service-level unit tests, and a real UoW against a test database for integration tests.

## Code style

- Type hints everywhere; the codebase should pass `mypy` (and/or `ty`) cleanly.
- `ruff check --fix` + `ruff format` for linting/formatting — via `uv run ruff ...`.
- Prefer `async def` endpoints and async DB access when the project's driver/session setup supports it; don't mix sync and async DB calls in the same path.
- Keep Pydantic schemas and ORM models named distinctly (e.g. `UserCreate`/`UserRead` vs `User`).
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

## Working style

- Show the modern, idiomatic pattern first; when something is unclear, explain the mechanism instead of falling back to a simplified version.
- When an edit is approved, change only the files that were named; if more files are needed for it to work, list them and ask first.
- Questions about code ("why", "how does this work") are answered without editing anything.

---

# This project

Learning project: FastAPI + async SQLAlchemy with Repository + Unit of Work.

## Layout

- `src/` is the package root (every directory has `__init__.py`); use absolute imports `from src...`.
- `src/main.py` — app entrypoint (lifespan, `api_router`, exception handlers); the CLI finds it via `[tool.fastapi] entrypoint = "src.main:app"` in `pyproject.toml`.
- `src/core/config.py` — `Settings` (`app_name`, `debug`, `api_v1_prefix`, `postgres_dsn`) + `get_settings()`.
- `src/core/exception_handlers.py` — `DomainException` → HTTP response (`register_exception_handlers(app)`).
- `src/core/db/` — `base.py` (`Base` = plain `DeclarativeBase`, ORM `IDMixin` / `TimestampMixin`), `db.py` (`engine`, `async_session_factory`), `models.py` (`User`, `Item`), `schemas.py` (Pydantic schemas + `IDMixin` / `TimestampMixin` / `ORMReadMixin`).
- `src/core/uow.py` — `AbstractUnitOfWork` / `SQLAlchemyUnitOfWork`.
- `src/core/security.py` — `hash_password` / `verify_password` (Argon2 via `pwdlib`).
- `src/repositories/` — `base.py` (`AbstractRepository`, `SQLAlchemyRepository`), `user.py` (`AbstractUserRepository`, `SQLAlchemyUserRepository`), `item.py` (`SQLAlchemyItemRepository`).
- `src/services/` — `user.py` (`UserService`), `item.py` (`ItemService`), `exceptions.py` (domain exceptions).
- `src/api/deps.py` — dependencies (`get_uow`, `UoWDep`, `get_user_service` / `UserServiceDep`, `get_item_service` / `ItemServiceDep`); routers in `src/api/v1/routes/` (`user.py`, `item.py`), aggregated by `src/api/v1/main.py` (`api_router`).
- `alembic/` + `alembic.ini` — migrations (async template); `alembic/env.py` takes the URL from `get_settings().postgres_dsn` and `Base.metadata` as `target_metadata`, models are imported there so autogenerate sees them.

## Project decisions

- Python 3.14 (`.python-version`, `requires-python = ">=3.14"`): PEP 695 generics in `repositories/base.py`, no `TypeVar` / `Generic`.
- `Item` exists only together with its `User`: `ForeignKey("user.id", ondelete="CASCADE")` + `cascade="all, delete-orphan"` on `User.items`.
- User schemas: `UserRegister` (public sign-up), `UserCreate` (admin), `UserPublic` (other users), `UserRead` (admin), `UserReadWithItems` (needs `selectinload(User.items)` in the repository).
- Plain `DeclarativeBase`, no `MappedAsDataclass` — deliberate, keep it simple for now.
- Updates: explicit field assignments while a schema has only a few fields (switch to a `setattr` loop over an allow-list at ~5-6); update schemas are PATCH-shaped (optional fields).
- Exception base class is `DomainException` (not `DomainError`); its handler is `domain_exception_handler`.
- Password hashing: `pwdlib` (`PasswordHash.recommended()`, Argon2id) — not `passlib`. The salt lives inside the hash string, so `User` has a single `hashed_password` column.
- `repo.delete(id)` does `session.get` + `session.delete`: the second lookup hits the session's identity map (no extra query), so keeping the id-based signature is accepted for now. Passing the loaded object (`delete(obj)`) is the stricter option from the general rules, not a bug.

## Local dev

- `docker compose up -d` — Postgres 18 (`postgres:18`), db `my_fastapi`, port 5432, named volume at `/var/lib/postgresql`. Docker Desktop (WSL 2) must be running on Windows.
- `.env` (gitignored): `POSTGRES_DSN=postgresql+asyncpg://user:password@localhost:5432/my_fastapi` (matches the compose file); add `DEBUG=true` locally if wanted.
- Migrations: `uv run alembic revision --autogenerate -m "<message>"` (review the generated file in `alembic/versions/`), then `uv run alembic upgrade head`; `uv run alembic current` shows the revision, `uv run alembic downgrade -1` rolls back one step.
- Run: `uv run fastapi dev` (dev, reload, 127.0.0.1:8000) / `uv run fastapi run` (prod mode, 0.0.0.0); deps have `fastapi[standard]`. `uv run uvicorn src.main:app --reload` also works. Docs at `/docs`.
- Checks: `uv run ruff check --diff` (preview, writes nothing), `uv run ruff check --fix`, `uv run ruff format`, `uv run mypy src`, `uv run pytest`. Commit before running `--fix` so its changes can be reverted with `git restore .`.

## Status / TODO

Keep this section current.

- Exceptions have no readable messages for `UserNotFound` / `UserAlreadyExists` / `ItemNotFound` (`detail` shows just the id); give them messages like `ItemAccessDenied`.
- No authorization: item routes take `user_id` from the path, so anyone can act as any user. Next step: login (`verify_password`, JWT via `PyJWT`) + `OAuth2PasswordBearer` + a `CurrentUserDep`.
- `ruff check` still reports 8 fixable issues (imports/`UP` rules in `alembic/env.py`, the first migration and `routes/item.py`; `env.py` needs `# noqa: F401` on the `models` import) and `ruff format` would reformat 3 files; `temp.py` in the repo root is a scratch file with undefined names — delete it.
- No tests (`tests/`), no `.env.example`; no `[tool.ruff]` / `[tool.mypy]` / `[tool.pytest.ini_options]` sections in `pyproject.toml` (the tools themselves are dev dependencies).
