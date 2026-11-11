from abc import abstractmethod
import uuid

from sqlalchemy import delete, func, select

from app.db.models import Task
from app.repositories.base import SQLAlchemyRepository, AbstractRepository


class AbstractTaskRepository(AbstractRepository[Task]):
    @abstractmethod
    async def get_all_users_task(
        self,
        user_id: uuid.UUID,
        *,
        limit: int,
        offset: int,
    ) -> list[Task]: ...

    @abstractmethod
    async def count_by_owner(self, user_id: uuid.UUID) -> int: ...

    @abstractmethod
    async def delete_all(self, user_id: uuid.UUID) -> None: ...

    @abstractmethod
    async def delete_all_except_groups_tasks(self, user_id: uuid.UUID) -> None: ...


class SQLAlchemyTaskRepository(SQLAlchemyRepository[Task], AbstractTaskRepository):
    model = Task

    async def get_all_users_task(
        self,
        user_id: uuid.UUID,
        *,
        limit: int,
        offset: int,
    ) -> list[Task]:
        stmt = (
            select(Task)
            .where(Task.created_by_id == user_id)
            .order_by(Task.created_at.desc(), Task.id.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_by_owner(self, user_id: uuid.UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(Task)
            .where(Task.created_by_id == user_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def delete_all(self, user_id: uuid.UUID) -> None:
        await self.session.execute(
            delete(Task).where(Task.created_by_id == user_id)
        )

    async def delete_all_except_groups_tasks(self, user_id: uuid.UUID) -> None:
        stmt = delete(Task).where(
            Task.created_by_id == user_id,
            Task.group_id.is_(None),
        )
        await self.session.execute(stmt)