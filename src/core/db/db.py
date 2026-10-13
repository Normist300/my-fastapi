from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.core.config import get_settings

engine: AsyncEngine = create_async_engine(
    get_settings().postgres_dsn,
    pool_pre_ping=True, # это общая рекомендация SQLAlchemy для прода
)

async_session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine,
    expire_on_commit=False, # официальная рекомендация именно для async-сессий
)