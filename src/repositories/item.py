from src.core.db.models import Item
from src.repositories.base import SQLAlchemyRepository


class SQLAlchemyItemRepository(SQLAlchemyRepository[Item]):
    model = Item
