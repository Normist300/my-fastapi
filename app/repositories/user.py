from abc import abstractmethod

from asyncpg import UniqueViolationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.db.models import User
from app.repositories.base import AbstractRepository, SQLAlchemyRepository
from app.services.exceptions import UserAlreadyExistsRepo


class AbstractUserRepository(AbstractRepository[User]):
    @abstractmethod
    async def get_by_email(self, email: str) -> User | None: ...


class SQLAlchemyUserRepository(SQLAlchemyRepository[User], AbstractUserRepository):
    model = User

    async def add_one(self, obj: User) -> User:
        try:
            return await super().add_one(obj)
        except IntegrityError as exc:
            original = exc.orig
            cause = original.__cause__ if original is not None else None

            if (
                isinstance(cause, UniqueViolationError) # Ошибка вызвана нарушением уникальности (уже существует с таким значением)
                and getattr(cause, "constraint_name", None) == "ix_user_email" # Ошибка именно из-за email
            ):
                raise UserAlreadyExistsRepo(obj.email) from exc

            raise



    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()
