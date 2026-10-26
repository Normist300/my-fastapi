from datetime import UTC, datetime, timedelta
import uuid

import pytest
from pydantic import SecretStr

from src.core.config import get_settings
from src.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from src.services.exceptions import InvalidToken
from tests.unit.helpers import make_token


def test_access_token_round_trip_returns_same_user_id() -> None:
    user_id = uuid.uuid4()

    token = create_access_token(user_id)

    assert decode_access_token(token) == user_id


def test_garbage_token_is_rejected() -> None:
    with pytest.raises(InvalidToken):
        decode_access_token("not-a-token")


def test_token_signed_with_other_key_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    token = create_access_token(uuid.uuid4())
    monkeypatch.setattr(
        get_settings(), "secret_key", SecretStr("other-key-" + "x" * 32)
    )

    with pytest.raises(InvalidToken):
        decode_access_token(token)


def test_token_with_not_uuid_sub_is_rejected() -> None:
    token = make_token(sub="abc")

    with pytest.raises(InvalidToken):
        decode_access_token(token)


def test_token_with_expired_time_is_rejected() -> None:
    token = make_token(exp=(datetime.now(UTC) - timedelta(minutes=1)))

    with pytest.raises(InvalidToken):
        decode_access_token(token)


@pytest.mark.parametrize(
    "drop",
    [
        frozenset({"sub"}),
        frozenset({"exp"}),
        frozenset({"sub", "exp"}),
    ],
)
def test_token_without_sub_or_exp_is_rejected(drop: frozenset) -> None:
    token = make_token(drop=drop)

    with pytest.raises(InvalidToken):
        decode_access_token(token)


def test_password_hash_not_equal_password() -> None:
    password = "test_password"

    assert hash_password(password) != password


def test_password_verify() -> None:
    password = "test_password"

    hashed_password = hash_password(password)

    assert verify_password(password, hashed_password)


@pytest.mark.parametrize(
    "wrong_password", ["", "Test_password", "test_password ", "123"]
)
def test_verify_password_rejects_wrong_password(wrong_password: str) -> None:
    password = "test_password"

    hashed_password = hash_password(password)
    bool_verify = verify_password(wrong_password, hashed_password)

    assert bool_verify == False


def test_two_equal_hashed_password_not_equal() -> None:
    password = "test_password"

    hashed_password_1 = hash_password(password)
    hashed_password_2 = hash_password(password)

    assert hashed_password_1 != hashed_password_2
