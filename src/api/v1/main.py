from fastapi import APIRouter

from src.api.v1.routes import item, user, auth

api_router = APIRouter()
api_router.include_router(user.router)
api_router.include_router(item.router)
api_router.include_router(auth.router)
