import uuid
from typing import ClassVar

from fastapi import status


class DomainException(Exception):
    status_code: ClassVar[int] = status.HTTP_400_BAD_REQUEST

#region Base exc
class NotFoundError(DomainException):
    status_code = status.HTTP_404_NOT_FOUND
class AlreadyExistsError(DomainException):
    status_code = status.HTTP_409_CONFLICT
class PermissionDeniedError(DomainException):
    status_code = status.HTTP_403_FORBIDDEN
#endregion

#region User
class UserAlreadyExists(AlreadyExistsError): ...
class UserNotFound(NotFoundError): ...
#endregion

#region Item
class ItemNotFound(NotFoundError): ...
class ItemAccessDenied(PermissionDeniedError):
    def __init__(self, item_id: uuid.UUID, user_id: uuid.UUID) -> None:
        self.item_id = item_id
        self.user_id = user_id
        super().__init__(f"User with id={user_id} has no access to item with id={item_id}")
#endregion