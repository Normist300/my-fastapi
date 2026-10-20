from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from src.api.deps import AuthServiceDep
from src.core.db.schemas import Token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
async def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    service: AuthServiceDep,
) -> Token:
    return await service.login(form.username, form.password)
