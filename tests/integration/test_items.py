import uuid
from typing import Any

import pytest
from httpx import AsyncClient

from src.core.uow import AbstractUnitOfWork
from tests.helpers import AuthHeaders, MakeUser

TITLE = "title"
DESCRIPTION = "description"


async def create_item(
        client: AsyncClient,
        headers: AuthHeaders,
        title: str = TITLE,
        description: str = DESCRIPTION) -> str:
    response = await client.post(
        "/items/", headers=headers, json={"title": title, "description": description}
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def test_item_created_can_be_read_back(
    client: AsyncClient, make_user: MakeUser
) -> None:
    headers = await make_user("test@examle.com")
    item_id = await create_item(client, headers)

    response = await client.get(f"/items/{item_id}", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == TITLE
    assert body["description"] == DESCRIPTION


@pytest.mark.parametrize(
    ("method", "json"),
    [
        pytest.param("GET", None, id="get"),
        pytest.param("PATCH", {"title": "stolen"}, id="patch"),
        pytest.param("DELETE", None, id="delete"),
    ],
)
async def test_item_of_other_user_is_forbidden_and_stays_unchanged(
    client: AsyncClient,
    make_user: MakeUser,
    method: str,
    json: dict[str, Any] | None,
) -> None:
    owner_headers = await make_user("owner@examle.com")
    other_headers = await make_user("other@examle.com")
    item_id = await create_item(client, owner_headers)

    response = await client.request(
        method, f"/items/{item_id}", headers=other_headers, json=json
    )

    assert response.status_code == 403
    owner_view = await client.get(f"/items/{item_id}", headers=owner_headers)
    assert owner_view.status_code == 200
    assert owner_view.json()["title"] == TITLE


async def test_all_users_item_is_gotten_without_others_users_item(
        client: AsyncClient,
        make_user: MakeUser,
) -> None:
    email = "owner@examle.com"
    email_other = "other@examle.com"
    headers = await make_user(email)
    headers_other = await make_user(email_other)
    id_item_1 = await create_item(client, headers, "item_1", "desc_1")
    id_item_2 = await create_item(client, headers, "item_2", "desc_2")
    id_item_other = await create_item(client, headers_other, "item_other", "desc_other")

    response = await client.get("/items/", headers=headers)

    assert response.status_code == 200
    body: list = response.json()
    ids = [item['id'] for item in body]
    assert id_item_1 in ids and id_item_2 in ids
    assert id_item_other not in ids
    



async def test_item_patch_persists_new_values(
    client: AsyncClient, make_user: MakeUser
) -> None:
    headers = await make_user("test@examle.com")
    item_id = await create_item(client, headers)
    json_patch = {"title": "new_title", "description": "new_description"}

    response = await client.patch(f"/items/{item_id}", headers=headers, json=json_patch)

    assert response.status_code == 200
    body = (await client.get(f"/items/{item_id}", headers=headers)).json()
    assert body["title"] == json_patch["title"]
    assert body["description"] == json_patch["description"]


async def test_item_patch_keeps_unsent_fields(
    client: AsyncClient, make_user: MakeUser
) -> None:
    headers = await make_user("test@examle.com")
    item_id = await create_item(client, headers)

    response = await client.patch(
        f"/items/{item_id}", headers=headers, json={"title": "new_title"}
    )

    assert response.status_code == 200
    body = (await client.get(f"/items/{item_id}", headers=headers)).json()
    assert body["title"] == "new_title"
    assert body["description"] == DESCRIPTION


async def test_item_patch_null_description_clears_it(
    client: AsyncClient, make_user: MakeUser
) -> None:
    headers = await make_user("test@examle.com")
    item_id = await create_item(client, headers)

    response = await client.patch(
        f"/items/{item_id}", headers=headers, json={"description": None}
    )

    assert response.status_code == 200
    body = (await client.get(f"/items/{item_id}", headers=headers)).json()
    assert body["description"] is None
    assert body["title"] == TITLE


async def test_item_patch_null_title_is_rejected(
    client: AsyncClient, make_user: MakeUser
) -> None:
    headers = await make_user("test@examle.com")
    item_id = await create_item(client, headers)

    response = await client.patch(
        f"/items/{item_id}", headers=headers, json={"title": None}
    )

    assert response.status_code == 422
    body = (await client.get(f"/items/{item_id}", headers=headers)).json()
    assert body["title"] == TITLE


async def test_item_deleted_is_not_found(
    client: AsyncClient, make_user: MakeUser
) -> None:
    headers = await make_user("test@examle.com")
    item_id = await create_item(client, headers)

    deleted = await client.delete(f"/items/{item_id}", headers=headers)
    assert deleted.status_code == 204

    response = await client.get(f"/items/{item_id}", headers=headers)

    assert response.status_code == 404


async def test_item_unknown_id_is_not_found(
    client: AsyncClient, make_user: MakeUser
) -> None:
    headers = await make_user("test@examle.com")

    response = await client.get(f"/items/{uuid.uuid4()}", headers=headers)

    assert response.status_code == 404


async def test_user_deletion_deletes_their_items(
    client: AsyncClient, uow: AbstractUnitOfWork, make_user: MakeUser
) -> None:
    headers = await make_user("test@examle.com")
    item_id = await create_item(client, headers)

    deleted = await client.delete("/users/me", headers=headers)
    assert deleted.status_code == 204

    async with uow:
        assert await uow.items.get_one(uuid.UUID(item_id)) is None
