from abc import ABC, abstractmethod
from typing import Self
from src.repositories.base import AbstractRepository
from src.core.db.models import User, Item

from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from src.repositories.user import UserRepository, AbstractUserRepository
from src.repositories.item import ItemRepository

class AbstractUnitOfWork(ABC):
    users: AbstractUserRepository
    items: AbstractRepository[Item]

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.rollback()

    @abstractmethod
    async def rollback(self) -> None:
        pass

    @abstractmethod
    async def commit(self) -> None:
        pass


class SQLAlchemyUnitOfWork(AbstractUnitOfWork):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory

    async def __aenter__(self) -> Self:
        self.session = self.session_factory()
        self.users = UserRepository(self.session)
        self.items = ItemRepository(self.session)
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await super().__aexit__(exc_type, exc, tb) # здесь roolback из абстракции
        return await self.session.close()

    async def rollback(self) -> None:
        await self.session.rollback()

    async def commit(self) -> None:
        await self.session.commit()