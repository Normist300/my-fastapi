from abc import abstractmethod
import uuid
import logging

from sqlalchemy import delete, exists, func, select

from app.db.models import Task, User, Group, GroupMember
from app.repositories.base import SQLAlchemyRepository, AbstractRepository

logger = logging.getLogger(__name__)

class AbstractGroupRepository(AbstractRepository[Group]):
    @abstractmethod
    async def is_member(self, user_id: uuid.UUID, group_id: uuid.UUID) -> bool: ...

    @abstractmethod
    async def add_member(self, user_id: uuid.UUID, group_id: uuid.UUID) -> GroupMember: ...

    @abstractmethod
    async def get_by_name(self, name: str) -> Group | None: ...

    @abstractmethod
    async def remove_member(self, user_id: uuid.UUID, group_id: uuid.UUID) -> None: ...


class SQLAlchemyGroupRepository(SQLAlchemyRepository[Group], AbstractGroupRepository):
    model = Group

    async def is_member(self, user_id: uuid.UUID, group_id: uuid.UUID) -> bool:
        stmt = select(
            exists().where(
                GroupMember.user_id == user_id,
                GroupMember.group_id == group_id,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()
    
    async def add_member(self, user_id: uuid.UUID, group_id: uuid.UUID) -> GroupMember:
        obj = GroupMember(user_id=user_id, group_id=group_id)
        self.session.add(obj)
        await self.session.flush()
        return obj

    async def get_by_name(self, name: str) -> Group | None:
        stmt = select(Group).where(Group.name == name)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def remove_member(self, user_id: uuid.UUID, group_id: uuid.UUID) -> None:
        membership = await self.session.get(
            GroupMember,
            {"user_id": user_id, "group_id": group_id},
        )
        if membership is not None:
            await self.session.delete(membership)