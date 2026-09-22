import uuid
from datetime import UTC, datetime

from pydantic import EmailStr
from sqlalchemy import ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
# from sqlmodel import DateTime, Field, SQLModel, Relationship

from src.core.db.base import (
    Base,
    UUIDPKMixin,
    TimestampMixin
)
class User(Base, UUIDPKMixin, TimestampMixin):
    '''ORM-Таблица пользователей'''
    __tablename__ = "user"

    email: Mapped[str] = mapped_column(unique=True, index=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    is_superuser: Mapped[bool] = mapped_column(default=False)
    full_name: Mapped[str | None] = mapped_column(default=None)
    hashed_password: Mapped[str]

    items: Mapped[list[Item]] = relationship(
        back_populates="owner",
        cascade="all, delete-orphan"
        )

class Item(Base, UUIDPKMixin, TimestampMixin):
    '''ORM-Таблица предметов'''
    __tablename__ = "item"

    title: Mapped[str]
    description: Mapped[str | None] = mapped_column(default=None)
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"))

    owner: Mapped[User | None] = relationship(back_populates="items")