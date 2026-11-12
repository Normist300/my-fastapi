import logging
import uuid

from app.db.models.group import Group
from app.db.schemas import GroupCreate, GroupMemberRead, GroupRead, GroupUpdate
from app.core.uow import AbstractUnitOfWork
from app.core.exceptions import (
    GroupAlreadyExists,
    GroupMemberNotFound,
    GroupNotFound,
    GroupAccessDenied,
    GroupMemberAlreadyExists
)

logger = logging.getLogger(__name__)


class GroupService:
    def __init__(self, uow: AbstractUnitOfWork) -> None:
        self.uow = uow

    async def _get_group_and_ensure_owner(self, user_id: uuid.UUID, group_id: uuid.UUID) -> Group:
        group = await self.uow.group.get_one(group_id)
        if group is None:
            raise GroupNotFound(group_id)
        if group.owner_id != user_id:
            raise GroupAccessDenied(group_id, user_id)

        return group

    async def create_group(self, owner_id: uuid.UUID, data: GroupCreate) -> GroupRead:
        async with self.uow:
            if await self.uow.group.get_by_name(data.name) is not None:
                raise GroupAlreadyExists(data.name)
            group = Group(**data.model_dump(), owner_id=owner_id)
            await self.uow.group.add_one(group)
            await self.uow.commit()

            logger.info(
                "Group=%s was created by user_id=%s",
                data.name,
                owner_id,
            )

            return GroupRead.model_validate(group)

    async def get_group(self, group_id: uuid.UUID) -> GroupRead:
        async with self.uow:
            group = await self.uow.group.get_one(group_id)
            if group is None:
                raise GroupNotFound(group_id)

            return GroupRead.model_validate(group)

    async def update_group(self, owner_id: uuid.UUID, group_id: uuid.UUID, data: GroupUpdate) -> GroupRead:
        async with self.uow:
            group = await self._get_group_and_ensure_owner(owner_id, group_id)

            for field, value in data.model_dump(exclude_unset=True).items():
                setattr(group, field, value)
            await self.uow.commit()

            logger.info(
                "Group was updated id=%s, owner=%s",
                group_id,
                owner_id,
            )

            return GroupRead.model_validate(group)

    async def delete_group(self, owner_id: uuid.UUID, group_id: uuid.UUID) -> None:
        async with self.uow:
            await self._get_group_and_ensure_owner(owner_id, group_id)
            await self.uow.group.delete(group_id)
            await self.uow.commit()

            logger.info(
                "Group was deleted id=%s, owner=%s",
                group_id,
                owner_id,
            )

    async def add_member(self, owner_id: uuid.UUID, user_id: uuid.UUID, group_id: uuid.UUID) -> GroupMemberRead:
        async with self.uow:
            await self._get_group_and_ensure_owner(owner_id, group_id)
            if await self.uow.group.is_member(user_id, group_id) is not None:
                raise GroupMemberAlreadyExists(user_id, group_id)
            group_member = await self.uow.group.add_member(user_id, group_id)
            await self.uow.commit()

            logger.info(
                "User is now a member of group | user_id=%s | group_id=%s",
                user_id,
                group_id,
            )

            return GroupMemberRead.model_validate(group_member)

    async def remove_member(self, owner_id: uuid.UUID, user_id: uuid.UUID, group_id: uuid.UUID) -> None:
        async with self.uow:
            await self._get_group_and_ensure_owner(owner_id, group_id)
            if await self.uow.group.is_member(user_id, group_id) is None:
                raise GroupMemberNotFound(user_id, group_id)
            await self.uow.group.remove_member(user_id, group_id)
            await self.uow.commit()

            logger.info(
                "User removed from group | user_id=%s",
                user_id,
                group_id,
            )

    async def leave_member(self, user_id: uuid.UUID, group_id: uuid.UUID) -> None:
        async with self.uow:
            if await self.uow.group.is_member(user_id, group_id) is None:
                raise GroupMemberNotFound(user_id, group_id)
            await self.uow.group.remove_member(user_id, group_id)
            await self.uow.commit()

            logger.info(
                "User leave from group user_id=%s",
                user_id,
                group_id,
            )