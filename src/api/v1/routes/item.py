import uuid

from fastapi import APIRouter, status

from src.api.deps import ItemServiceDep, CurrentUserDep
from src.core.db.schemas import ItemCreate, ItemRead, ItemUpdate

router = APIRouter(prefix="/items", tags=["items"])


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_item(
    user: CurrentUserDep, data: ItemCreate, service: ItemServiceDep
) -> ItemRead:
    return await service.create(user.id, data)


@router.get("/")
async def get_all_items(user: CurrentUserDep, service: ItemServiceDep) -> list[ItemRead]:
    return await service.get_all_users_item(user.id)


@router.get("/{item_id}")
async def get_item(
    item_id: uuid.UUID, user: CurrentUserDep, service: ItemServiceDep
) -> ItemRead:
    return await service.get(item_id, user.id)


@router.patch("/{item_id}")
async def update_item(
    item_id: uuid.UUID, user: CurrentUserDep, data: ItemUpdate, service: ItemServiceDep
) -> ItemRead:
    return await service.update(item_id, user.id, data)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(
    item_id: uuid.UUID, user: CurrentUserDep, service: ItemServiceDep
) -> None:
    await service.delete(item_id, user.id)
