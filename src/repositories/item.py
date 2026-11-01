from abc import abstractmethod
import uuid

from sqlalchemy import select

from src.core.db.models import Item, User
from src.repositories.base import SQLAlchemyRepository, AbstractRepository


class AbstractItemRepository(AbstractRepository[Item]):
    @abstractmethod
    async def get_all_users_item(self,
                                 user_id: uuid.UUID,
                                 *,
                                 limit: int,
                                 offset: int,                                 
                                 ) -> list[Item]: ...


class SQLAlchemyItemRepository(SQLAlchemyRepository[Item], AbstractItemRepository):
    model = Item

    async def get_all_users_item(self,
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