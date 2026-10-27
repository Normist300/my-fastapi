from collections.abc import AsyncGenerator

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    async_sessionmaker,
    create_async_engine,
)
from httpx import ASGITransport, AsyncClient, Response

from src.core.uow import AbstractUnitOfWork, SQLAlchemyUnitOfWork
from src.core.config import get_settings
from src.main import app
from src.api.deps import get_uow
from tests.helpers import PASSWORD, SECRET_FIELDS, MakeUser, AuthHeaders



@pytest.fixture(scope="session")
def migrated_db() -> None:
    dsn = get_settings().postgres_dsn.get_secret_value()
    assert dsn.endswith("_test"), "тесты запускаются только на тестовой БД (в названии бд в конце не '_test')"
    command.upgrade(Config("alembic.ini"), "head")


@pytest.fixture(scope="session")
async def engine(migrated_db: None) -> AsyncGenerator[AsyncEngine]:
    engine = create_async_engine(get_settings().postgres_dsn.get_secret_value())
    yield engine
    await engine.dispose()


@pytest.fixture
async def connection(engine: AsyncEngine) -> AsyncGenerator[AsyncConnection]:
    async with engine.connect() as conn:
        transaction = await conn.begin()
        yield conn
        await transaction.rollback()


@pytest.fixture
def uow(connection: AsyncConnection) -> AbstractUnitOfWork:
    session_factory = async_sessionmaker(
        bind=connection,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )
    return SQLAlchemyUnitOfWork(session_factory)


async def check_no_secret(response: Response) -> None:
    await response.aread()
    request = response.request
    leaked = [secret for secret in SECRET_FIELDS if secret in response.text]
    assert not leaked, f"{request.url} {request.method} раскрывает {leaked}"


@pytest.fixture
async def client(uow: AbstractUnitOfWork) -> AsyncGenerator[AsyncClient]:
    app.dependency_overrides[get_uow] = lambda: uow
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url=f"http://test{get_settings().api_v1_prefix}",
        event_hooks={"response": [check_no_secret]},
    ) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
def make_user(client: AsyncClient) -> MakeUser:
    async def _make_user(email: str) -> AuthHeaders:
        response = await client.post(
            "/users/", json={"email": email, "password": PASSWORD}
        )
        assert response.status_code == 201, response.text
        response = await client.post(
            "/auth/login", data={"username": email, "password": PASSWORD}
        )
        assert response.status_code == 200, response.text
        return {"Authorization": f"Bearer {response.json()['access_token']}"}
    return _make_user