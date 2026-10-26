import pytest
from pydantic import ValidationError

from src.core.db.schemas import ItemUpdate


def test_ItemUpdate_with_explicitly_title_is_null_is_rejected() -> None:
    with pytest.raises(ValidationError):
        ItemUpdate(title=None)


def test_ItemUpdate_without_explicitly_title_is_unset() -> None:
    assert "title" not in ItemUpdate().model_dump(exclude_unset=True)
