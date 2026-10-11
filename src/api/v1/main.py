from fastapi import APIRouter

from src.api.v1.routes import user, item

api_router = APIRouter()
api_router.include_router(user.router)
api_router.include_router(item.router)