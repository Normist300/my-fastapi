from abc import ABC, abstractmethod
from typing import TypeVar, Generic
from src.repositories.base import AbstractRepository
from pydantic import EmailStr

from src.repositories.base import SQLAlchemyRepository
from src.core.db.models import User

from sqlalchemy import select

class AbstractUserRepository(AbstractRepository[User]):
    @abstractmethod
    async def get_by_email(self, email: EmailStr) -> User | None:
        pass


class UserRepository(SQLAlchemyRepository[User], AbstractUserRepository):
    model = User

    async def get_by_email(self, email: EmailStr) -> User | None:
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalar()