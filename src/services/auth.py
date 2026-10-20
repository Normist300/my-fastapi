from src.core.uow import AbstractUnitOfWork
from src.services.exceptions import UserInactive, InvalidCredentials, InvalidToken
from src.core.security import (
    verify_password,
    DUMMY_HASH,
    create_access_token,
    decode_access_token,
)
from src.core.db.schemas import Token, UserRead


class AuthService:
    def __init__(self, uow: AbstractUnitOfWork) -> None:
        self.uow = uow

    async def login(self, email: str, password: str) -> Token:
        async with self.uow:
            user = await self.uow.users.get_by_email(email)
            if user is None:
                verify_password(password, DUMMY_HASH)
                raise InvalidCredentials()
            if not verify_password(password, user.hashed_password):
                raise InvalidCredentials()
            if not user.is_active:
                raise UserInactive()
            return Token(access_token=create_access_token(user.id))

    async def get_current_user(self, token: str) -> UserRead:
        user_id = decode_access_token(token)
        async with self.uow:
            user = await self.uow.users.get_one(user_id)
            if user is None:
                raise InvalidToken()
            if not user.is_active:
                raise UserInactive()
            return UserRead.model_validate(user)
