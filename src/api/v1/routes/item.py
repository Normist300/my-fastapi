import uuid

from fastapi import APIRouter, status

from src.api.dep import ItemServiceDep
from src.core.db.schemas import (
    ItemCreate,
    ItemRead,
    ItemUpdate
)

router = APIRouter(prefix="/items", tags=["items"])


@router.post("/{user_id}", status_code=status.HTTP_201_CREATED)
async def add_item_to_user(
    user_id: uuid.UUID, data: ItemCreate,
    service: ItemServiceDep
    ) -> ItemRead:
    return await service.create(user_id, data)


@router.get("/{user_id}/{item_id}")
async def get_item(
    item_id: uuid.UUID, user_id: uuid.UUID,
    service: ItemServiceDep
    ) -> ItemRead:
    return await service.get(item_id, user_id)


@router.patch("/{user_id}/{item_id}")
async def update_item(
    item_id: uuid.UUID, user_id: uuid.UUID, data: ItemUpdate,
    service: ItemServiceDep) -> ItemRead:
    return await service.update(item_id, user_id, data)


@router.delete("")
async def delete_item(
    item_id: uuid.UUID, user_id: uuid.UUID,
    service: ItemServiceDep) -> None:
    await service.delete(item_id, user_id)