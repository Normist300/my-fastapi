import uuid

from fastapi import APIRouter, status

from src.api.dep import UserServiceDep
from src.core.db.schemas import UserPublic, UserRegister, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/", status_code=status.HTTP_201_CREATED)
async def register_user(data: UserRegister, service: UserServiceDep) -> UserPublic:
    return await service.register(data)

@router.get("/{user_id}")
async def get_user(user_id: uuid.UUID, service: UserServiceDep) -> UserPublic:
    return await service.get(user_id)

@router.patch("/{user_id}")
async def update_user(user_id: uuid.UUID,
                      data: UserUpdate,
                      service: UserServiceDep) -> UserPublic:
    return await service.update(user_id, data)

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: uuid.UUID, service: UserServiceDep) -> None:
    await service.delete(user_id)