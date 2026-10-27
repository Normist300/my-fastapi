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
- Secrets (`secret_key`, a DSN that contains a password) are `SecretStr`; unwrap with `.get_secret_value()` only at the point of use (`jwt.encode`, `create_async_engine`). Same for incoming passwords in input schemas (`UserRegister.password: SecretStr`, unwrapped right before `hash_password`) — it masks them in `repr`/logs and marks them `format: password` in OpenAPI. Functions and services take plain `str`; ORM models never use `SecretStr` (`Mapped[...]` takes Python types).

## Database (PostgreSQL, async)

- Async driver: `asyncpg` by default (`postgresql+asyncpg://...`). Consider `psycopg` (3.x async) only for API parity with existing sync code or psycopg-specific features (COPY, server-side cursors).
- `create_async_engine(..., pool_pre_ping=True)` to avoid stale pooled connections.
- `async_sessionmaker(engine, expire_on_commit=False)` — required for usable attribute access on ORM objects after `commit()` in async code.
- Local Postgres via Docker Compose (official `postgres` image, named volume for persistence). Note: the data volume path changed with Postgres 18 (`/var/lib/postgresql`, not the older `/var/lib/postgresql/data`) — check the image's docs when bumping the major version.
- Publish the port as `127.0.0.1:5432:5432` (a bare `5432:5432` listens on every interface). `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` are applied only when the volume is first initialised: change a password later with `ALTER USER` (`docker compose exec postgres psql -U <user> -d postgres -c "..."`), create extra databases (the test DB) with `docker compose exec postgres createdb -U <user> <name>`. `exec` runs inside the running container and connects over the local socket, so no password is asked.

## Architecture: Repository + Unit of Work

Default to this layering unless a project's existing code already does something else — in that case, follow the existing pattern and flag the mismatch rather than silently introducing a repository layer.

- **Routers** (`api/routes/*.py`) — thin. Parse/validate input via Pydantic, call a service, map the result to a response schema. No direct ORM/session access.
  - REST paths: plural nouns, no verbs (`/items/{item_id}`, not `/items/get/...`) — the HTTP method is the action; multi-word path segments in kebab-case, path params in snake_case. Endpoints about the caller live under `/me` (`/users/me`).
  - Literal paths go before parameterized ones with the same method (`/me` before `/{user_id}`): routes are matched top-down by path pattern only, and type validation runs after the match (`me` as a UUID → 422).
  - Function names become the `operationId` and the Swagger summary, so they are unique and action-shaped: `create_item`, `get_item`, `list_items`, `update_item`, `delete_item`, `read_me`.
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
  - Updates: a separate update schema with optional fields (PATCH semantics) and `model_dump(exclude_unset=True)`; apply it with explicit assignments, or a `setattr` loop only over an explicit allow-list of fields (the schema alone must not be the only guard — an `owner_id` added later would become writable). Never let `None` through for non-nullable columns: reject an explicit `null` in the update schema — a `@field_validator` that raises on `None` (defaults aren't validated, so an omitted field still passes) or, on Pydantic 2.14+, the `MISSING` sentinel (`title: str | MISSING = Field(default=MISSING, ...)`) — not by skipping `None` in the service, which also blocks clearing nullable fields.
  - Repeated "load or raise" goes into a private helper (`async def _get_or_raise(self, id) -> User`, always `await`ed) used inside the `async with self.uow:` block.
  - Deletes: the service loads the object (raising `NotFound`), then calls `repo.delete(obj)`; the repository takes the already-loaded object and never silently no-ops. The second lookup would hit the session's identity map anyway (one session = one `async with self.uow:` block), but passing the object keeps it explicit.
  - Don't call another service's method inside an open `async with self.uow:` — FastAPI caches `get_uow` per request, so services share one UoW instance, and re-entering it replaces `self.session` (the outer work is silently lost).
- **Domain exceptions**: services raise domain exceptions, never `HTTPException`. Keep them in `services/exceptions.py` as a hierarchy on `Exception` (`DomainException` → `NotFoundError` / `AlreadyExistsError` → `UserNotFound`, ...), pass the relevant data to `super().__init__(message)`. Each branch carries its HTTP status as a class attribute (`status_code: ClassVar[int] = status.HTTP_404_NOT_FOUND`, `from fastapi import status` — same constants as in the routers, one style across the project); subclasses inherit it and override only when they need a different code. One `exception_handler` on `DomainException` (registered from `main.py`) builds the response from `exc.status_code` + the message — no separate exception → status mapping table. Response headers are declared the same way (`headers: ClassVar[dict[str, str] | None] = None` on `DomainException`, `{"WWW-Authenticate": "Bearer"}` on `AuthenticationError`, 401) and the handler passes `headers=exc.headers`. Every exception has a readable message (fixed in its `__init__` or built from its data) — otherwise the response is `{"detail": ""}`. Deliberate trade-off: strict layer purity isn't a goal here. Register it as `app.exception_handler(DomainException)(domain_exception_handler)` (not `add_exception_handler`: mypy rejects a handler typed `exc: DomainException` there); name unused handler parameters `_` (`_: Request`).
- **App entrypoint** (`main.py`): `FastAPI(title=settings.app_name, debug=settings.debug, lifespan=lifespan)`, one aggregating `api_router` per API version (`api/v1/main.py` includes the entity routers, `main.py` mounts it with `settings.api_v1_prefix`), then the exception handlers. `lifespan` is an `@asynccontextmanager` annotated `-> AsyncGenerator[None]` (not `AsyncIterator`, which is deprecated for this; for `@contextmanager` use `Generator[None]`) that does `await engine.dispose()` after `yield`; tables come from Alembic, not `create_all`.
- **UoW `__aexit__`**: rollback in `try`, `session.close()` in `finally`, so a failing rollback doesn't leak the connection.
- **Dependencies** (`api/deps.py` — the composition root, lives in the API layer because it's FastAPI-specific): `get_uow()` is a plain function returning `AbstractUnitOfWork` (not a `yield` dependency — commits stay in services); expose `Annotated` aliases (`UoWDep`, `UserServiceDep`); no session dependency for routers. Tests swap implementations via `app.dependency_overrides[get_uow]`.
- **Auth (OAuth2 password flow + JWT)**: `core/security.py` holds password hashing and `create_access_token` / `decode_access_token` (PyJWT, `sub` = user id, `exp` required; any decode error → `InvalidToken`). `AuthService.login(email, password)` checks the password *before* `is_active` (only someone who knows the password learns the account is inactive), verifies against a `DUMMY_HASH` when the email is unknown (same timing), and uses one generic message ("Incorrect email or password"); the login route takes `OAuth2PasswordRequestForm` (`username` carries the email). `get_current_user` in `api/deps.py` (`OAuth2PasswordBearer(tokenUrl=<full login path>)` → `AuthService.get_current_user`) reloads the user from the DB on every request and checks `is_active`, so deleted/deactivated users lose access before `exp`; routes get it as `CurrentUserDep`. The acting user's id always comes from the token, never from the path or body. Tokens are stateless: logout is client-side and revocation is only via `is_active`, so access tokens stay short-lived.

For tests, services and API run with the real `SQLAlchemyUnitOfWork` against a test database (see Testing); fakes behind the same abstract interfaces only for dependencies that can't run locally.

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

- pytest + pytest-asyncio, configured in the native `[tool.pytest]` table (pytest 9+): `pythonpath = ["."]`, `asyncio_mode = "auto"`, and both `asyncio_default_fixture_loop_scope` and `asyncio_default_test_loop_scope` set to `"session"` — the session-scoped engine's asyncpg connections are bound to the event loop they were opened in.
- Layout: `tests/unit/` (pure logic: no DB, no app import) and `tests/integration/` (test DB + HTTP). The top-level `tests/conftest.py` only writes test env values; DB and client fixtures live in `tests/integration/conftest.py` (a `conftest.py` is loaded by pytest and visible to its directory and below). Shared constants, type aliases and helpers go in `tests/helpers.py` — tests don't import from a `conftest.py`.
- Test doubles by fidelity: the real implementation first, then a fake, a mock only as a last resort. Your own database is always real: services, repositories and API run against a dedicated test Postgres database, each test isolated by rolling back its transaction. Fakes are for dependencies that can't run locally (external APIs, email, payments). No mocks that assert on call sequences — they test the implementation, not the behavior.
- A fake implements the same abstract interface as the real thing and fills in whatever the real dependency would (e.g. DB-side defaults: ORM column defaults are applied only on `flush()`, so without a DB `id`, `created_at`, `is_active` stay `None`).
- Test settings: `conftest.py` writes test values (`SECRET_KEY`, `POSTGRES_DSN`) to `os.environ` before anything imports `src` — env vars override `.env`, and `get_settings()` is `lru_cache`d. Per-test changes go through `monkeypatch.setattr(get_settings(), ...)`, which is undone after the test.
- Test DB fixtures (`tests/integration/conftest.py`): a separate `<db>_test` database; a session-scoped **sync** fixture guards the DSN (`assert dsn.endswith("_test")`) and runs `command.upgrade(Config("alembic.ini"), "head")` (sync because the async `env.py` calls `asyncio.run`); a session-scoped `engine`; a per-test `connection` with an outer transaction rolled back after the test; `async_sessionmaker(bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint")`, so the services' `commit()` only releases a SAVEPOINT; the real `SQLAlchemyUnitOfWork` on top, injected with `app.dependency_overrides[get_uow] = lambda: uow` and cleared after the test; `httpx.AsyncClient(transport=ASGITransport(app=app), base_url=f"http://test{api_v1_prefix}")` (it doesn't run `lifespan`).
- Logged-in users come from a factory fixture (`make_user(email) -> auth headers`: register + log in). Login is a form (`data=`, not `json=`); request paths match the route exactly (an extra trailing slash → 307 redirect, which httpx doesn't follow). State the API can't produce (an inactive user) is set up through the same `uow` fixture.
- Assert status codes and the values that express business rules: data round-trips, ownership (403 on someone else's object, which stays in place), 404 after delete, the same 401 + `WWW-Authenticate` for a wrong password and an unknown email, 403 for an inactive user only with the correct password, tokens of deactivated/deleted users stop working. Don't assert response field sets or whole bodies — response schemas are the allow-list, and repeating them is a change-detector test.
- One global guard for data that must never leave the server: secret columns are marked `mapped_column(info={"secret": True})`; `SECRET_FIELDS` is collected from `Base.registry.mappers` (import the models module first and assert the set is non-empty); an httpx `event_hooks={"response": [...]}` check (`await response.aread()` first) fails on any response that contains one.
- Test what can break the app — own logic, own configuration of libraries (e.g. `options={"require": [...]}` in `jwt.decode`), error paths — not the library itself or plain declarations (`model_fields`, status-code class attributes): check those through behavior in service/API tests. A negative test must fail for the intended reason only (break exactly one thing; keep a control test that the unbroken input passes), and every new test is seen failing once (break the code or the input temporarily).
- Test helpers don't copy the code under test: produce valid input with the public function and break one thing through a setting (`monkeypatch` the key, the expiry); build raw input by hand only where it comes from outside (a token without `sub`). Field and column names come from the code (`User.is_superuser.key`, column `info`), never hardcoded strings that keep passing after a rename. `assert` on a generator is always true — collect a list (`leaked = [...]; assert not leaked, msg`) or use `all()`.
- A known open bug gets a test marked `@pytest.mark.xfail(reason=..., strict=True)` until it's fixed.
- One test module per feature/router; name tests after the behavior, not the function: `test_<subject>_<condition>_<outcome>` in snake_case. Name `parametrize` cases with `pytest.param(..., id="...")`.
- Run the full suite via `uv run pytest` before considering backend work done (integration tests need Docker running).

## Working style

- Show the modern, idiomatic pattern first; when something is unclear, explain the mechanism instead of falling back to a simplified version.
- When an edit is approved, change only the files that were named; if more files are needed for it to work, list them and ask first.
- Questions about code ("why", "how does this work") are answered without editing anything.
- Example code handed to the user is run first (a scratch copy of the project, a temporary or test DB), and the reply says whether it was verified.
- Give one settled recommendation. When the user pushes back, re-evaluate honestly and restate the final rule in one place instead of amending it piece by piece.

---

# This project

Learning project: FastAPI + async SQLAlchemy with Repository + Unit of Work.

## Layout

- `src/` is the package root (every directory has `__init__.py`); use absolute imports `from src...`.
- `src/main.py` — app entrypoint (lifespan, `api_router`, exception handlers); the CLI finds it via `[tool.fastapi] entrypoint = "src.main:app"` in `pyproject.toml`.
- `src/core/config.py` — `Settings` (`app_name`, `debug`, `api_v1_prefix`, `access_token_expire_minutes`; `postgres_dsn` and `secret_key` as `SecretStr`) + `get_settings()`.
- `src/core/exception_handlers.py` — `DomainException` → HTTP response (`register_exception_handlers(app)`).
- `src/core/db/` — `base.py` (`Base` = plain `DeclarativeBase`, ORM `IDMixin` / `TimestampMixin`), `db.py` (`engine`, `async_session_factory`), `models.py` (`User`, `Item`), `schemas.py` (Pydantic schemas + `IDMixin` / `TimestampMixin` / `ORMReadMixin`).
- `src/core/uow.py` — `AbstractUnitOfWork` / `SQLAlchemyUnitOfWork`.
- `src/core/security.py` — `hash_password` / `verify_password` (Argon2 via `pwdlib`), `DUMMY_HASH`, `create_access_token` / `decode_access_token` (PyJWT, HS256).
- `src/repositories/` — `base.py` (`AbstractRepository`, `SQLAlchemyRepository`), `user.py` (`AbstractUserRepository`, `SQLAlchemyUserRepository`), `item.py` (`SQLAlchemyItemRepository`).
- `src/services/` — `user.py` (`UserService`), `item.py` (`ItemService`), `auth.py` (`AuthService`: `login`, `get_current_user`), `exceptions.py` (domain exceptions).
- `src/api/deps.py` — dependencies (`get_uow`, `UoWDep`, `get_user_service` / `UserServiceDep`, `get_item_service` / `ItemServiceDep`, `get_auth_service` / `AuthServiceDep`, `oauth2_scheme`, `get_current_user` / `CurrentUserDep`); routers in `src/api/v1/routes/` (`user.py`, `item.py`, `auth.py`), aggregated by `src/api/v1/main.py` (`api_router`).
- `alembic/` + `alembic.ini` — migrations (async template); `alembic/env.py` takes the URL from `get_settings().postgres_dsn` and `Base.metadata` as `target_metadata`, models are imported there so autogenerate sees them.
- `tests/` — `conftest.py` (test `SECRET_KEY` / `POSTGRES_DSN` → `my_fastapi_test`), `helpers.py` (`SECRET_FIELDS`, `PASSWORD`, `AuthHeaders` / `MakeUser`); `unit/` (`test_security.py` with its own `helpers.py` / `make_token`, `test_helpers.py`, `test_schemas.py`); `integration/` (`conftest.py`: `migrated_db`, `engine`, `connection`, `uow`, `client` with the `check_no_secret` response hook; `test_users.py`, `test_auth.py`).

## Project decisions

- Python 3.14 (`.python-version`, `requires-python = ">=3.14"`): PEP 695 generics in `repositories/base.py`, no `TypeVar` / `Generic`.
- `Item` exists only together with its `User`: `ForeignKey("user.id", ondelete="CASCADE")` + `cascade="all, delete-orphan"` on `User.items`.
- User schemas: `UserRegister` (public sign-up), `UserCreate` (admin), `UserPublic` (other users), `UserRead` (admin), `UserReadWithItems` (needs `selectinload(User.items)` in the repository).
- Plain `DeclarativeBase`, no `MappedAsDataclass` — deliberate, keep it simple for now.
- Updates: explicit field assignments while a schema has only a few fields (switch to a `setattr` loop over an allow-list at ~5-6); update schemas are PATCH-shaped (optional fields).
- Exception base class is `DomainException` (not `DomainError`); its handler is `domain_exception_handler`.
- Password hashing: `pwdlib` (`PasswordHash.recommended()`, Argon2id) — not `passlib`. The salt lives inside the hash string, so `User` has a single `hashed_password` column.
- `repo.delete(id)` does `session.get` + `session.delete`: the second lookup hits the session's identity map (no extra query), so keeping the id-based signature is accepted for now. Passing the loaded object (`delete(obj)`) is the stricter option from the general rules, not a bug.

- Auth: OAuth2 password flow + JWT access token, no refresh tokens yet. `POST /auth/login` (form-data) → `Token`; protected routes take `CurrentUserDep` (`UserRead`). Item routes are `/items/` and `/items/{item_id}` for the current user; self-service is under `/users/me` (`GET`, `PATCH`, `DELETE`); `POST /users/` (registration) and `GET /users/{user_id}` (`UserPublic`) stay public.
- `ItemUpdate.title` rejects an explicit `null` with a `field_validator` (the `MISSING`-sentinel version is left commented in `schemas.py` for when the project moves to Pydantic 2.14+); `ItemService.update` applies whatever was sent, so `{"description": null}` clears the description.
- `User.hashed_password` is marked `info={"secret": True}`; tests collect such columns into `SECRET_FIELDS` and fail on any response that contains one.
- Tests: no fakes for the own DB (the decision and its reasons are in Testing); unit tests cover `security.py` and the `ItemUpdate` validator only — tests that duplicate declarations or library behavior (salted hashes differ, `model_fields`, field sets of responses) were dropped on purpose.

## Local dev

- `docker compose up -d` — Postgres 18 (`postgres:18`), db `my_fastapi`, port 5432, named volume at `/var/lib/postgresql`. Docker Desktop (WSL 2) must be running on Windows.
- `.env` (gitignored): `POSTGRES_DSN=postgresql+asyncpg://user:password@localhost:5432/my_fastapi` (matches the compose file); add `DEBUG=true` locally if wanted. `SECRET_KEY` (JWT signing key) is generated with `uv run python -c "import secrets; print(secrets.token_hex(32))"`; changing it invalidates every issued token.
- Migrations: `uv run alembic revision --autogenerate -m "<message>"` (review the generated file in `alembic/versions/`), then `uv run alembic upgrade head`; `uv run alembic current` shows the revision, `uv run alembic downgrade -1` rolls back one step. `Target database is not up to date` on autogenerate means the existing migrations aren't applied to this DB yet — run `upgrade head` first.
- Run: `uv run fastapi dev` (dev, reload, 127.0.0.1:8000) / `uv run fastapi run` (prod mode, 0.0.0.0); deps have `fastapi[standard]`. `uv run uvicorn src.main:app --reload` also works. Docs at `/docs`.
- Tests: `docker compose exec postgres createdb -U user my_fastapi_test` once; the `migrated_db` fixture applies the migrations itself. `uv run pytest` (needs Docker for `tests/integration/`), `uv run pytest tests/unit` without it.
- Checks: `uv run ruff check --diff` (preview, writes nothing), `uv run ruff check --fix`, `uv run ruff format`, `uv run mypy src`, `uv run pytest`. Commit before running `--fix` so its changes can be reverted with `git restore .`.

## Status / TODO

Keep this section current.

- Exceptions have no readable messages for `UserNotFound` / `UserAlreadyExists` / `ItemNotFound` (`detail` shows just the id); give them messages like `ItemAccessDenied`.
- Refresh tokens (long sessions without long-lived access tokens) — later.
- `ruff check` reports 27 issues (26 fixable: mostly import sorting, unused imports, `UP` rules) and `ruff format` would reformat 6 files; `temp.py` in the repo root is a scratch file with undefined names — delete it. `mypy src tests` is clean.
- Tests: unit tests done; integration tests for users and auth started, items still to write (someone else's item → 403 and stays, 404 after delete, PATCH keeps unsent fields / clears `description` / rejects `title: null`, deleting a user deletes their items). The unreadable-404 exception messages above will show up there as failing tests.
- `docker-compose.yml` publishes Postgres as `5432:5432` (all interfaces) — bind it to `127.0.0.1:5432:5432`.
- No `[tool.ruff]` / `[tool.mypy]` sections in `pyproject.toml` (`[tool.pytest]` is configured).
