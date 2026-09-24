from src.repositories.base import SQLAlchemyRepository
from src.core.db.models import User

class UserRepository(SQLAlchemyRepository[User]):
    model = User