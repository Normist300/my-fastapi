import uuid

from fastapi import APIRouter, status

from src.api.deps import UserServiceDep, CurrentUserDep
from src.core.db.schemas import UserPublic, UserRegister, UserUpdate, UserRead

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/", status_code=status.HTTP_201_CREATED)
async def register_user(data: UserRegister, service: UserServiceDep) -> UserPublic:
    return await service.register(data)


@router.get("/me")
async def read_me(user: CurrentUserDep) -> UserRead:
    return user


@router.get("/{user_id}")
async def get_user_by_id(user_id: uuid.UUID, service: UserServiceDep) -> UserPublic:
    return await service.get(user_id)


@router.patch("/me")
async def update_me(
    user: CurrentUserDep, data: UserUpdate, service: UserServiceDep
) -> UserPublic:
    return await service.update(user.id, data)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user: CurrentUserDep, service: UserServiceDep) -> None:
    await service.delete(user.id)
