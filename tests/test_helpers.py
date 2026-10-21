import uuid

from tests.helpers import make_token
from src.core.security import decode_access_token


def test_make_token_default_is_accepted() -> None:
    user_id = uuid.uuid4()

    assert decode_access_token(make_token(user_id=user_id)) == user_id
