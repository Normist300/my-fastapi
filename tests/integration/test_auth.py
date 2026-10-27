from httpx import AsyncClient
import pytest

from src.core.uow import AbstractUnitOfWork
from tests.helpers import PASSWORD, AuthHeaders, MakeUser


async def deactivate(uow: AbstractUnitOfWork, email: str) -> None:
    async with uow:
        user = await uow.users.get_by_email(email)
        assert user is not None
        user.is_active = False
        await uow.commit()


async def test_login_token_gives_access_to_own_profile(
    client: AsyncClient,
    make_user: MakeUser,
) -> None:
    email = "test@examle.com"
    headers = await make_user(email)

    response = await client.get("/users/me", headers=headers)

    assert response.status_code == 200
    assert response.json()["email"] == email


async def test_wrong_password_and_unknown_email_get_same_401(
    client: AsyncClient,
    make_user: MakeUser,
) -> None:
    email = "test@examle.com"
    unknown_email = "unknown@examle.com"
    await make_user(email)

    wrong_password_response = await client.post(
        "auth/login", data={"username": email, "password": "wrong-password"}
    )
    unknown_email_response = await client.post(
        "auth/login", data={"username": unknown_email, "password": PASSWORD}
    )

    assert (
        wrong_password_response.status_code == unknown_email_response.status_code == 401
    )
    assert wrong_password_response.json() == unknown_email_response.json()
    assert wrong_password_response.headers["WWW-Authenticate"] == "Bearer"


@pytest.mark.parametrize(
    ("password", "expected_status"),
    [
        pytest.param(PASSWORD, 403, id="correct-password"),
        pytest.param("wrong-password", 401, id="wrong-password"),
    ],
)
async def test_inactive_user_learns_about_it_only_with_correct_password(
    client: AsyncClient,
    uow: AbstractUnitOfWork,
    make_user: MakeUser,
    password: str,
    expected_status: int,
) -> None:
    email = "test@examle.com"
    await make_user(email)
    await deactivate(uow, email)

    response = await client.post(
        "/auth/login", data={"username": email, "password": password}
    )

    assert response.status_code == expected_status


async def test_token_of_deactivated_user_stops_working(
        client: AsyncClient, uow: AbstractUnitOfWork, make_user: MakeUser,
) -> None:
    email = "test@examle.com"
    headers = await make_user(email)
    await deactivate(uow, email)

    response = await client.get("/users/me", headers=headers)

    assert response.status_code == 403


async def test_token_of_deleted_user_stops_working(
        client: AsyncClient, make_user: MakeUser,
) -> None:
    email = "test@examle.com"
    headers = await make_user(email)
    deleted = await client.delete("/users/me", headers=headers)
    assert deleted.status_code == 204

    response = await client.get("/users/me", headers=headers)

    assert response.status_code == 401


@pytest.mark.parametrize(
        "headers",
        [
            pytest.param({}, id="no-token"),
            pytest.param({"Authorization": "Bearer garbage"}, id="garbage-token"),
        ],
)
async def test_protected_route_rejects_missing_or_bad_token(
    client: AsyncClient, headers: AuthHeaders,
) -> None:
    response = await client.get("/users/me", headers=headers)

    assert response.status_code == 401