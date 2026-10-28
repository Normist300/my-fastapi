from httpx import AsyncClient
import pytest

from src.core.uow import AbstractUnitOfWork
from src.services.exceptions import UserAlreadyExists
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