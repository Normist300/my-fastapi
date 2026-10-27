import src.core.db.models # Для Base
from src.core.db.base import Base
from src.core.db.models import User

from collections.abc import Awaitable, Callable

SECRET_FIELDS = frozenset(
    prop.key
    for mapper in Base.registry.mappers
    for prop in mapper.column_attrs
    if prop.columns[0].info.get("secret")
)
assert SECRET_FIELDS, "ни одна колонка не помечена secret"

PASSWORD = "password"

type AuthHeaders = dict[str, str]
type MakeUser = Callable[[str], Awaitable[AuthHeaders]]