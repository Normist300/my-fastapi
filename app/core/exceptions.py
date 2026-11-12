import uuid
from typing import ClassVar

from fastapi import status


class DomainException(Exception):
    status_code: ClassVar[int] = status.HTTP_400_BAD_REQUEST
    headers: ClassVar[dict[str, str] | None] = None


# region Base exc
class NotFoundError(DomainException):
    status_code = status.HTTP_404_NOT_FOUND


class AlreadyExistsError(DomainException):
    status_code = status.HTTP_409_CONFLICT


class PermissionDeniedError(DomainException):
    status_code = status.HTTP_403_FORBIDDEN


class AuthenticationError(DomainException):
    status_code = status.HTTP_401_UNAUTHORIZED
    headers = {"WWW-Authenticate": "Bearer"}


# endregion


# region User
class UserAlreadyExists(AlreadyExistsError):
    def __init__(self, email: str) -> None:
        super().__init__(f"User with email={email} already exists")


class UserAlreadyExistsRepo(AlreadyExistsError):
    def __init__(self, email: str) -> None:
        super().__init__(f"User with email={email} already exists. Layer: repo")


class UserNotFound(NotFoundError): 
    def __init__(self, user_id: uuid.UUID) -> None:
        super().__init__(f"User with id={user_id} not found")

class UserInactive(PermissionDeniedError):
    def __init__(self) -> None:
        super().__init__("Inactive user")


class InvalidCredentials(AuthenticationError):
    def __init__(self) -> None:
        super().__init__("Incorrect email or password")


class InvalidToken(AuthenticationError):
    def __init__(self) -> None:
        super().__init__("Could not validate credentials")


# endregion


# region Task
class TaskNotFound(NotFoundError): ...


class TaskAccessDenied(PermissionDeniedError):
    def __init__(self, task_id: uuid.UUID, user_id: uuid.UUID) -> None:
        self.task_id = task_id
        self.user_id = user_id
        super().__init__(
            f"User with id={user_id} has no access to task with id={task_id}"
        )
# endregion

# region Group
class GroupAccessDenied(PermissionDeniedError):
    def __init__(self, group_id: uuid.UUID | None, user_id: uuid.UUID) -> None:
        self.group_id = group_id
        self.user_id = user_id
        super().__init__(
            f"User with id={user_id} has no access to group with id={group_id}"
        )
# endregion
