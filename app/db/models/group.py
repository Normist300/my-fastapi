import uuid

from sqlalchemy import Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base, IDMixin, TimestampMixin
from app.db.enums import TaskStatus

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app.db.models.task import Task
    from app.db.models.user import User


class Group(Base, IDMixin, TimestampMixin):
    """
    Группы юзеров с групповыми тасками
    """

    __tablename__ = "task_group"

    name: Mapped[str]

    """Связи написаны с двух сторон, но не все они нужны"""
    tasks: Mapped[list[Task]] = relationship(
        back_populates="group", cascade="all, delete-orphan"
    )
    # memberships: Mapped[list[GroupMember]] = relationship(
    #     back_populates="group",
    #     cascade="all, delete-orphan",
    #     passive_deletes=True,
    # )


class GroupMember(Base, TimestampMixin):
    """
    Таблица отражающая членство юзеров в группах
    """

    __tablename__ = "task_group_member"
    group_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("task_group.id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"),
        primary_key=True,
    )

    """Связи написаны с двух сторон, но не все они нужны"""
    # group: Mapped[Group] = relationship(back_populates="memberships")
    # user: Mapped[User] = relationship(back_populates="memberships")
