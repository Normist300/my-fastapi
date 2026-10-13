import uuid
from abc import ABC, abstractmethod

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.db.base import Base


class AbstractRepository[ModelType: Base](ABC):
    @abstractmethod
    async def add_one(self, obj: ModelType) -> ModelType: ...

    @abstractmethod
    async def get_one(self, id: uuid.UUID) -> ModelType | None: ...

    @abstractmethod
    async def find_all(self) -> list[ModelType]: ...

    @abstractmethod
    async def delete(self, id: uuid.UUID) -> None: ...

class SQLAlchemyRepository[ModelType: Base](AbstractRepository[ModelType]):
    model: type[ModelType]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add_one(self, obj: ModelType) -> ModelType:
        self.session.add(obj)
        await self.session.flush()
        return obj

    async def get_one(self, id: uuid.UUID) -> ModelType | None:
        return await self.session.get(self.model, id)

    async def find_all(self) -> list[ModelType]:
        result = await self.session.execute(select(self.model))
        return list(result.scalars().all())

    async def delete(self, id: uuid.UUID) -> None:
        # Всегда удаляется таким способом: найти -> удалить
        obj = await self.session.get(self.model, id)
        if obj is not None:
            await self.session.delete(obj)