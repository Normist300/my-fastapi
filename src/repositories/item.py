from src.repositories.base import SQLAlchemyRepository
from src.core.db.models import Item

class SQLAlchemyItemRepository(SQLAlchemyRepository[Item]):
    model = Item