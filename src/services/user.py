import uuid

from src.core.uow import AbstractUnitOfWork
from src.core.db.models import User
from src.core.security import hash_password
from src.core.db.schemas import (
    UserRegister,
    UserPublic,
    UserUpdate
)
from src.services.exceptions import (
    UserNotFound,
    UserAlreadyExists
)


class UserService:
    def __init__(self, uow: AbstractUnitOfWork) -> None:
        self.uow = uow

    async def register(self, data: UserRegister) -> UserPublic:
        async with self.uow: # Начало блока транзакции
            if await self.uow.users.get_by_email(data.email) is not None:
                raise UserAlreadyExists(data.email)

            user = User(
                email=data.email,
                full_name=data.full_name,
                hashed_password=hash_password(data.password)
            )
            await self.uow.users.add_one(user)
            await self.uow.commit()
            return UserPublic.model_validate(user)

    async def get(self, id: uuid.UUID) -> UserPublic:
        async with self.uow:
            user = await self.uow.users.get_one(id)
            if user is None:
                raise UserNotFound(id)
            return UserPublic.model_validate(user)

    # async def get_by_email(self, email: str) -> UserPublic:
    #     async with self.uow:
    #         user = await self.uow.users.get_by_email(email)
    #         if user is None:
    #             raise UserNotFound(email)
    #         return UserPublic.model_validate(user)

    async def update(self, id: uuid.UUID, data: UserUpdate) -> UserPublic:
        async with self.uow:
            user = await self.uow.users.get_one(id)
            if user is None:
                raise UserNotFound(id)

            for field, value in data.model_dump(exclude_unset=True).items():
                setattr(user, field, value)

            await self.uow.commit()
            return UserPublic.model_validate(user)