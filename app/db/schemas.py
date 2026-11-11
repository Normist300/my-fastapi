from typing import Literal
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, SecretStr, field_validator

from app.db.enums import TaskStatus
from app.db.models.task import Task


# region Mixins
class IDMixin(BaseModel):
    id: uuid.UUID


class TimestampMixin(BaseModel):
    created_at: datetime
    updated_at: datetime

class GroupsIdsMixin(BaseModel):
    group_id: uuid.UUID | None
    created_by_id: uuid.UUID | None
    assignee_id:  uuid.UUID | None


class ORMReadMixin(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# endregion


# region User
class Token(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"


class UserBase(BaseModel):
    """НЕ давать заполнять клиенту"""

    email: EmailStr = Field(max_length=255)
    is_active: bool = True
    is_superuser: bool = False
    full_name: str | None = Field(default=None, max_length=255)


# Для заполнения клиентом
class UserRegister(BaseModel):
    """Для заполнения клиентом"""

    email: EmailStr = Field(max_length=255)
    password: SecretStr = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)


class UserUpdate(BaseModel):
    """Для заполнения клиентом"""
    # email: EmailStr = Field(max_length=255)
    full_name: str | None = Field(default=None, max_length=255)


# Для вывода
class UserPublic(IDMixin, TimestampMixin, ORMReadMixin):
    full_name: str | None = Field(default=None, max_length=255)


class UserRead(UserBase, IDMixin, TimestampMixin, ORMReadMixin): ...


class UserReadWithOwnTasks(UserRead):
    tasks_created_by_user: list[TaskRead]
# endregion


# region Task
class TaskBase(GroupsIdsMixin):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=255)
    status: TaskStatus = TaskStatus.TODO


class TaskCreate(TaskBase): ...


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    # если pydantic >= 2.14 (вышел 8 октября 2026), то можно так: (вместо title_is_not_null)
    # title: str | MISSING = Field(default=MISSING, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=255)
    status: TaskStatus = TaskStatus.TODO
    assignee_id:  uuid.UUID | None

    @field_validator("title")
    @classmethod
    def title_is_not_null(cls, value: str | None) -> str | None:
        if value is None:
            raise ValueError("title cannot be null")
        return value



class TaskRead(TaskBase, IDMixin, TimestampMixin, ORMReadMixin): ...
# endregion


#region Group
class GroupBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)

class GroupCreate(GroupBase): ...

class GroupUpdate(GroupBase): ...

class GroupRead(GroupBase, IDMixin, TimestampMixin, ORMReadMixin): ...

class GroupWithTasks(GroupRead):
    tasks: list[GroupRead]
#endregion

#region GroupMember
class GroupMemberBase(BaseModel):
    group_id: uuid.UUID
    user_id: uuid.UUID

class GroupMemberCreate(GroupMemberBase): ...

class GroupMemberRead(GroupMemberBase, TimestampMixin, ORMReadMixin): ...
#endregion





# class Message(BaseModel):
#     message: str
