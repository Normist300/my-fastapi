from abc import ABC, abstractmethod
from typing import TypeVar, Generic
from src.repositories.base import AbstractRepository

from src.repositories.base import SQLAlchemyRepository
from src.core.db.models import User

from sqlalchemy import select

class AbstractUserRepository(AbstractRepository[User]):
    @abstractmethod
    async def get_by_email(self, email: str) -> User | None: ...


class SQLAlchemyUserRepository(SQLAlchemyRepository[User], AbstractUserRepository):
    model = User

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()