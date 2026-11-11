import uuid

from sqlalchemy import Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base, IDMixin, TimestampMixin
from app.db.enums import TaskStatus

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app.db.models.group import GroupMember
    from app.db.models.task import Task


class User(Base, IDMixin, TimestampMixin):
    """ORM-Таблица пользователей"""

    __tablename__ = "user"

    email: Mapped[str] = mapped_column(unique=True, index=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    is_superuser: Mapped[bool] = mapped_column(default=False)
    full_name: Mapped[str | None] = mapped_column(default=None)
    hashed_password: Mapped[str] = mapped_column(info={"secret": True})

    tasks_created_by_user: Mapped[list[Task]] = relationship(foreign_keys="Task.owner_id")

    """Связи написаны с двух сторон, но не все они нужны"""
    # tasks_assigned_to_user: Mapped[list[Task]] = relationship(
    #     back_populates="assignee", foreign_keys="Task.assignee_id"
    # )
    # memberships: Mapped[list[GroupMember]] = relationship(
    #     back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    # )