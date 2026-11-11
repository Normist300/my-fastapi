import pytest
from pydantic import ValidationError

from app.db.schemas import TaskUpdate


def test_ItemUpdate_with_explicitly_title_is_null_is_rejected() -> None:
    with pytest.raises(ValidationError):
        TaskUpdate(title=None)


def test_ItemUpdate_without_explicitly_title_is_unset() -> None:
    assert "title" not in TaskUpdate().model_dump(exclude_unset=True)
