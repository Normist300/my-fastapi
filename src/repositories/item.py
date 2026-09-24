from src.repositories.base import SQLAlchemyRepository
from src.core.db.models import Item

class ItemRepository(SQLAlchemyRepository[Item]):
    model = Item