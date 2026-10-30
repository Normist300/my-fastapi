from abc import abstractmethod
import uuid

from sqlalchemy import select

from src.core.db.models import Item, User
from src.repositories.base import SQLAlchemyRepository, AbstractRepository


class AbstractItemRepository(AbstractRepository[Item]):
    @abstractmethod
    async def get_all_users_item(self, user_id: uuid.UUID) -> list[Item] | None: ...


class SQLAlchemyItemRepository(SQLAlchemyRepository[Item], AbstractItemRepository):
    model = Item

    async def get_all_users_item(self, user_id: uuid.UUID) -> list[Item] | None:
        result = await self.session.execute(select(Item).where(Item.owner_id == user_id))
        return list(result.scalars().all())