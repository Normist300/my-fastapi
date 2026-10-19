from typing import Annotated

from fastapi import Depends

from src.core.db.db import async_session_factory
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