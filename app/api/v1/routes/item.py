from typing import Annotated
import uuid

from fastapi import APIRouter, Query, status

from app.api.deps import ItemServiceDep, CurrentUserDep
from app.db.schemas import TaskCreate, TaskRead, TaskUpdate

router = APIRouter(prefix="/items", tags=["items"])


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_item(
    user: CurrentUserDep, data: TaskCreate, service: ItemServiceDep
) -> TaskRead:
    return await service.create(user.id, data)


@router.get("/")
async def get_all_items(
    user: CurrentUserDep,
    service: ItemServiceDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[TaskRead]:
    return await service.get_all_users_task(user.id, limit=limit, offset=offset)


@router.get("/{item_id}")
async def get_item(
    item_id: uuid.UUID, user: CurrentUserDep, service: ItemServiceDep
) -> TaskRead:
    return await service.get(item_id, user.id)


@router.patch("/{item_id}")
async def update_item(
    item_id: uuid.UUID, user: CurrentUserDep, data: TaskUpdate, service: ItemServiceDep
) -> TaskRead:
    return await service.update(item_id, user.id, data)


@router.delete("/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_all_item(user: CurrentUserDep, service: ItemServiceDep) -> None:
    await service.delete_all(user.id)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(
    item_id: uuid.UUID, user: CurrentUserDep, service: ItemServiceDep
) -> None:
    await service.delete(item_id, user.id)
