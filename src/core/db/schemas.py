from typing import Literal
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, SecretStr


# region Mixins
class IDMixin(BaseModel):
    id: uuid.UUID


class TimestampMixin(BaseModel):
    created_at: datetime
    updated_at: datetime


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
    email: EmailStr = Field(max_length=255)
    full_name: str | None = Field(default=None, max_length=255)


class UserRead(UserBase, IDMixin, TimestampMixin, ORMReadMixin):
    pass


# endregion


# region Item
class ItemBase(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=255)


class ItemCreate(ItemBase):
    # owner_id: uuid.UUID
    pass


class ItemUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=255)


class ItemRead(ItemBase, IDMixin, TimestampMixin, ORMReadMixin): ...


class ItemPublic(ItemRead): ...


# endregion


class UserReadWithItems(UserRead):
    items: list[ItemRead]


# class Message(BaseModel):
#     message: str
