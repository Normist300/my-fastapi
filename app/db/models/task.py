import uuid

from sqlalchemy import Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base, IDMixin, TimestampMixin
from app.db.enums import TaskStatus

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app.db.models.group import Group
    from app.db.models.user import User


class Task(Base, IDMixin, TimestampMixin):
    """
    ORM-Таблица задач
    Задачи существуют только вместе с owner
    """

    __tablename__ = "task"

    title: Mapped[str]
    description: Mapped[str | None] = mapped_column(default=None)
    status: Mapped[TaskStatus] = mapped_column(
        Enum(
            TaskStatus,
            native_enum=False,
            create_constraint=True,
            values_callable=lambda enum: [member.value for member in enum],
        ),
        default=TaskStatus.TODO,
    )
    group_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("task_group.id", ondelete="CASCADE")
    )
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("user.id", ondelete="SET NULL")
    )
    assignee_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("user.id", ondelete="SET NULL"), default=None
    )

    """Связи написаны с двух сторон, но не все они нужны"""
    # group: Mapped[Group | None] = relationship(back_populates="tasks")
    # owner: Mapped[User] = relationship(
    #     back_populates="tasks_created_by_user",
    #     foreign_keys=[owner_id],
    # )
    # assignee: Mapped[User | None] = relationship(
    #     back_populates="tasks_assigned_to_user",
    #     foreign_keys=[assignee_id]
    # )
