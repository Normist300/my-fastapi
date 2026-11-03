from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.main import api_router
from app.core.config import get_settings
from app.db.db import engine
from app.core.exception_handlers import register_exception_handlers
from app.core.logging_config import setup_logging
from app.core.middleware import log_request


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None]:
    setup_logging()
    yield
    await engine.dispose()


settings = get_settings()

app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=lifespan)
app.include_router(api_router, prefix=settings.api_v1_prefix)
register_exception_handlers(app)
app.middleware("http")(log_request)