import logging
import uuid

from app.db.models import Task
from app.db.schemas import TaskCreate, TaskRead, TaskUpdate
from app.core.uow import AbstractUnitOfWork
from app.core.exceptions import (
    TaskAccessDenied,
    TaskNotFound,
    UserNotFound,
    GroupAccessDenied,
)

logger = logging.getLogger(__name__)


class TaskService:
    def __init__(self, uow: AbstractUnitOfWork) -> None:
        self.uow = uow

    async def _check_group_access(
        self, group_id: uuid.UUID | None, user_id: uuid.UUID
    ) -> bool:
        if (
            group_id is not None
            and not await self.uow.group.is_member(user_id, group_id)
        ):
            return False
        return True

    async def _get_and_check_general_access(
        self, task_id: uuid.UUID, user_id: uuid.UUID
    ) -> Task:
        task = await self.uow.tasks.get_one(task_id)
        if task is None:
            raise TaskNotFound(task_id)
        elif self._check_group_access(task.group_id, user_id):
            raise GroupAccessDenied(task.group_id, user_id)
        elif task.group_id is None and task.created_by_id != user_id:
            raise TaskAccessDenied(task_id, user_id)
        return task
        

    async def create(self, user_id: uuid.UUID, data: TaskCreate) -> TaskRead:
        async with self.uow:
            if await self.uow.users.get_one(user_id) is None:
                raise UserNotFound(user_id)
            elif self._check_group_access(data.group_id, user_id):
                raise GroupAccessDenied(data.group_id, user_id)

            task = Task(
                **data.model_dump(),
                created_by_id=user_id,
            )
            await self.uow.tasks.add_one(task)
            await self.uow.commit()

            logger.info(
                "Task was created id=%s, created_by_id=%s",
                task.id,
                user_id,
            )

            return TaskRead.model_validate(task)

    async def get(self, task_id: uuid.UUID, user_id: uuid.UUID) -> TaskRead:
        async with self.uow:
            task = await self._get_and_check_general_access(task_id, user_id)
            return TaskRead.model_validate(task)

    async def get_all_users_task(
        self,
        user_id: uuid.UUID,
        *,
        limit: int,
        offset: int,
    ) -> list[TaskRead]:
        async with self.uow:
            tasks = await self.uow.tasks.get_all_users_task(
                user_id, limit=limit, offset=offset
            )

            return [TaskRead.model_validate(task) for task in tasks]

    async def update(
        self, task_id: uuid.UUID, user_id: uuid.UUID, data: TaskUpdate
    ) -> TaskRead:
        async with self.uow:
            task = await self._get_and_check_general_access(task_id, user_id)

            for field, value in data.model_dump(exclude_unset=True).items():
                setattr(task, field, value)
            await self.uow.commit()

            logger.info(
                "Task was updated id=%s, created_by_id=%s",
                task_id,
                user_id,
            )

            return TaskRead.model_validate(task)

    async def delete(self, task_id: uuid.UUID, user_id: uuid.UUID) -> None:
        async with self.uow:
            await self._get_and_check_general_access(task_id, user_id)

            await self.uow.tasks.delete(task_id)
            await self.uow.commit()

            logger.info(
                "Task was deleted id=%s, created_by_id=%s",
                task_id,
                user_id,
            )

    async def delete_all(self, user_id: uuid.UUID) -> None:
        async with self.uow:
            if await self.uow.tasks.count_by_owner(user_id) == 0:
                raise TaskNotFound()
            await self.uow.tasks.delete_all(user_id)
            await self.uow.commit()

            logger.info(
                "User was deleted all tasks user_id=%s",
                user_id,
            )
