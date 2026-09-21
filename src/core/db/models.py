import uuid
from datetime import UTC, datetime

from pydantic import EmailStr
from sqlmodel import DateTime, Field, SQLModel, Relationship

from src.core.db.schemas import (
    UserBase,
    ItemBase
)


def get_datetime_utc() -> datetime:
    return datetime.now(UTC)

class User(UserBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    hashed_password: str
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True), # type: ignore
    )
    items: list[Item] = Relationship(back_populates="owner", cascade_delete=True)

class Item(ItemBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime | None = Field(
            default_factory=get_datetime_utc,
            sa_type=DateTime(timezone=True), # type: ignore
        )
    owner_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE"
    )
    owner: User | None = Relationship(back_populates="items")