import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def get_datetime_utc() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class IDMixin:
    """Дополнение ID"""

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)


class TimestampMixin:
    """Дополнение время создания и обновления"""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=get_datetime_utc
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=get_datetime_utc, onupdate=get_datetime_utc
    )
