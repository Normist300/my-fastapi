from datetime import UTC, datetime

from pydantic import EmailStr
from sqlmodel import Field, SQLModel

def get_datetime_utc() -> datetime:
    return datetime.now(UTC)

class UserBase(SQLModel):
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    is_active: bool = True
    is_superuser: bool = False
    full_name: str | None = Field(default=None, max_length=255)