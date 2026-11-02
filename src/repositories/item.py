from abc import abstractmethod
import uuid

from sqlalchemy import delete, func, select

from src.core.db.models import Item, User
from src.repositories.base import SQLAlchemyRepository, AbstractRepository


class AbstractItemRepository(AbstractRepository[Item]):
    @abstractmethod
    async def get_all_users_item(
        self,
        user_id: uuid.UUID,
        *,
        limit: int,
        offset: int,
    ) -> list[Item]: ...

    @abstractmethod
    async def count_by_owner(self, user_id: uuid.UUID) -> int: ...

    @abstractmethod
    async def delete_all(self, user_id: uuid.UUID) -> None: ...


class SQLAlchemyItemRepository(SQLAlchemyRepository[Item], AbstractItemRepository):
    model = Item

    async def get_all_users_item(
        self,
        user_id: uuid.UUID,
        *,
        limit: int,
        offset: int,
    ) -> list[Item]:
        stmt = (
            select(Item)
            .where(Item.owner_id == user_id)
            .order_by(Item.created_at.desc(), Item.id.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_by_owner(self, user_id: uuid.UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(Item)
            .where(Item.owner_id == user_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def delete_all(self, user_id: uuid.UUID) -> None:
        await self.session.execute(
            delete(Item).where(Item.owner_id == user_id)
        )