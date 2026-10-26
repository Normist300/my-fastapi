import uuid
from datetime import UTC, datetime, timedelta

import jwt

from src.core.config import get_settings
from src.core.security import ALGORITHM


def make_token(
    *,
    user_id: uuid.UUID | None = None,
    drop: frozenset[str] = frozenset(),
    key: str | None = None,
    **claims: object,
) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    if user_id is None:
        user_id = uuid.uuid4()
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    payload.update(claims)
    for claim in drop:
        del payload[claim]
    if key is None:
        key = settings.secret_key.get_secret_value()
    return jwt.encode(
        payload=payload,
        key=key,
        algorithm=ALGORITHM,
    )
