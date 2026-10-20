from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

from src.core.config import get_settings
from src.core.db.db import async_session_factory
from src.core.db.schemas import UserRead
from src.core.uow import AbstractUnitOfWork, SQLAlchemyUnitOfWork
from src.services.item import ItemService
from src.services.user import UserService
from src.services.auth import AuthService


def get_uow() -> AbstractUnitOfWork:
    return SQLAlchemyUnitOfWork(async_session_factory)


UoWDep = Annotated[AbstractUnitOfWork, Depends(get_uow)]


def get_user_service(uow: UoWDep) -> UserService:
    return UserService(uow)


def get_item_service(uow: UoWDep) -> ItemService:
    return ItemService(uow)


def get_auth_service(uow: UoWDep) -> AuthService:
    return AuthService(uow)


UserServiceDep = Annotated[UserService, Depends(get_user_service)]
ItemServiceDep = Annotated[ItemService, Depends(get_item_service)]
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{get_settings().api_v1_prefix}/auth/login"
)


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)], service: AuthServiceDep
) -> UserRead:
    return await service.get_current_user(token)


CurrentUserDep = Annotated[UserRead, Depends(get_current_user)]
