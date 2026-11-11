import uuid
import logging

from app.db.models import User
from app.db.schemas import UserPublic, UserRegister, UserUpdate
from app.core.security import hash_password
from app.core.uow import AbstractUnitOfWork
from app.core.exceptions import UserAlreadyExists, UserNotFound

logger = logging.getLogger(__name__)

class UserService:
    def __init__(self, uow: AbstractUnitOfWork) -> None:
        self.uow = uow

    async def _get_or_raise(self, id: uuid.UUID) -> User:
        user = await self.uow.users.get_one(id)
        if user is None:
            raise UserNotFound(id)
        return user

    async def register(self, data: UserRegister) -> UserPublic:
        async with self.uow:  # Начало блока транзакции
            if await self.uow.users.get_by_email(data.email) is not None:
                raise UserAlreadyExists(data.email)

            user = User(
                email=data.email,
                full_name=data.full_name,
                hashed_password=hash_password(data.password.get_secret_value()),
            )
            await self.uow.users.add_one(user)
            await self.uow.commit()

            logger.info(
                "User was registered user_id=%s",
                user.id,
            )

            return UserPublic.model_validate(user)

    async def get(self, id: uuid.UUID) -> UserPublic:
        async with self.uow:
            user = await self._get_or_raise(id)
            return UserPublic.model_validate(user)

    # async def get_by_email(self, email: str) -> UserPublic:
    #     async with self.uow:
    #         user = await self.uow.users.get_by_email(email)
    #         if user is None:
    #             raise UserNotFound(email)
    #         return UserPublic.model_validate(user)

    async def update(self, id: uuid.UUID, data: UserUpdate) -> UserPublic:
        async with self.uow:
            user = await self._get_or_raise(id)
            for field, value in data.model_dump(exclude_unset=True).items():
                setattr(user, field, value)

            await self.uow.commit()

            logger.info(
                "User was updated user_id=%s",
                user.id,
            )
            
            return UserPublic.model_validate(user)

    async def delete(self, id: uuid.UUID) -> None:
        async with self.uow:
            await self._get_or_raise(id)
            await self.uow.tasks.delete_all_except_groups_tasks(id)
            await self.uow.users.delete(id)
            await self.uow.commit()

            logger.info(
                "User was deleted user_id=%s",
                id,
            )
