from httpx import AsyncClient
import pytest

from src.core.uow import AbstractUnitOfWork
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