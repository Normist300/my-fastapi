from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.core.db.db import engine
from src.core.config import get_settings
from src.core.exception_handlers import register_exception_handlers
from src.api.v1.main import api_router

@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None]:
    yield
    await engine.dispose()

settings = get_settings()

app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=lifespan)
app.include_router(api_router, prefix=settings.api_v1_prefix)
register_exception_handlers(app)