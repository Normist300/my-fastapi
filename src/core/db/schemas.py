import uuid
from datetime import UTC, datetime
from pydantic import EmailStr, Field, BaseModel, ConfigDict


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
class UserBase(BaseModel):
    '''НЕ давать заполнять клиенту'''
    email: EmailStr = Field(max_length=255)
    is_active: bool = True
    is_superuser: bool = False
    full_name: str | None = Field(default=None, max_length=255)

class UserRegister(BaseModel):
    '''Для заполнения клиентом'''
    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)

class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)

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
    pass

class ItemRead(ItemBase, IDMixin, TimestampMixin, ORMReadMixin):
    pass
# endregion

class UserReadWithItems(UserRead):
    items: list[ItemRead]