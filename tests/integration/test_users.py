import asyncio

from httpx import AsyncClient
import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from app.api.deps import get_uow
from app.db.models import User
from app.main import app
from app.core.uow import AbstractUnitOfWork, SQLAlchemyUnitOfWork
from app.repositories.user import SQLAlchemyUserRepository
from app.services.exceptions import UserAlreadyExists
from tests.helpers import PASSWORD, AuthHeaders, MakeUser


async def test_registration_returns_submitted_data(client: AsyncClient) -> None:
    email = "test@examle.com"
    json_post = {"email": email, "password": PASSWORD, "full_name": "Test"}
    response = await client.post(
                "/users/",
                json=json_post
            )

    assert response.status_code == 201
    body: dict = response.json()
    assert json_post["email"] == body["email"]
    assert json_post["full_name"] == body["full_name"]
    assert "password" not in body.keys()


async def test_registration_ignores_superuser_flag(client: AsyncClient) -> None:
    email = "test@examle.com"
    json_post = {"email": email, "password": PASSWORD, "full_name": "Test",
                 "is_superuser": True}
    await client.post("/users/",json=json_post)
    login = await client.post("/auth/login",
                              data={"username": email, "password": PASSWORD})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    response = await client.get("/users/me", headers=headers)

    assert response.status_code == 200
    assert response.json()["is_superuser"] is False


async def test_cannot_register_exist_user(client: AsyncClient, make_user: MakeUser) -> None:
    email_existed_user = "test@example.com"
    await make_user(email_existed_user)

    response = await client.post(
        "/users/", json={"email": email_existed_user, "password": PASSWORD}
    )

    assert response.status_code == 409


async def test_user_try_get_admin_access_is_ignore(client: AsyncClient, make_user: MakeUser) -> None:
    email_user = "test@example.com"
    headers = await make_user(email_user)

    await client.patch("/users/me", headers=headers, json={"full_name": "cool_name", "is_superuser": True})
    response = await client.get("/users/me", headers=headers)

    body = response.json()
    assert body["is_superuser"] == False
    assert body["full_name"] == "cool_name"


async def test_concurrent_registration_returns_201_and_409(
        client: AsyncClient,
        engine: AsyncEngine,
        monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Делаем два одинаковых запроса, но в разных ПОДКЛЮЧЕНИЯХ
    В фикстурах UoW делается в одном подключении. Поэтому переопределяем
    """

    email = "test@example.com"
    json_post = {"email": email, "password": PASSWORD}

    # Для получения разных connections
    session_factory = async_sessionmaker(
        bind=engine,
        expire_on_commit=False,
    )

    def get_uow_new() -> SQLAlchemyUnitOfWork:
        return SQLAlchemyUnitOfWork(session_factory)

    monkeypatch.setitem(
        app.dependency_overrides,
        get_uow,
        get_uow_new,
    )

    barrier = asyncio.Barrier(2)
    original_get_by_email = SQLAlchemyUserRepository.get_by_email

    async def sync_get_by_email(
            self: SQLAlchemyUserRepository,
            email_to_find: str,
    ) -> User | None:
        user = await original_get_by_email(self, email_to_find)

        if email_to_find == email:
            assert user is None

            await barrier.wait()

        return user

    monkeypatch.setattr(
        SQLAlchemyUserRepository,
        "get_by_email",
        sync_get_by_email,
    )

    try:
        async with asyncio.timeout(15): # Ограничиваем по времени, чтобы ничего не упало
            async with asyncio.TaskGroup() as group:
                first = group.create_task(
                    client.post("/users/", json=json_post)
                )
                second = group.create_task(
                    client.post("/users/", json=json_post)
                )

            responses = [first.result(), second.result()]
            assert sorted([r.status_code for r in responses]) == [201, 409], [(r.status_code, r.text) for r in responses]

            success = next(r for r in responses if r.status_code == 201)
            assert success.json()["email"] == email

            # Проверка состояния до коммита отдельной сессией
            async with session_factory() as session:
                result = await session.scalars(
                    select(User).where(User.email == email)
                )
                users = result.all()

                assert len(users) == 1
                assert str(users[0].id) == success.json()["id"]

    finally:
        # удаляем записи, так как у нас коммиты были в соединении
        # без "create_savepoint"
        async with session_factory.begin() as session:
            await session.execute(
                delete(User).where(User.email == email)
            )
