import uuid

from pydantic import EmailStr

from src.core.uow import AbstractUnitOfWork
from src.services.exceptions import UserInactive, InvalidCredentials
from src.core.security import verify_password, DUMMY_HASH, create_access_token
from src.core.db.schemas import Token

class AuthService:
    def __init__(self, uow: AbstractUnitOfWork) -> None:
        self.uow = uow

    async def login(self, email: EmailStr, password: str):
        user = await self.uow.users.get_by_email(email)
        if user is None:
            verify_password(password, DUMMY_HASH)
            raise InvalidCredentials()
        if not verify_password(password, user.hashed_password):
            return InvalidCredentials()
        if not user.is_active:
            return UserInactive()
        return Token(acces_token=create_access_token(user.id))