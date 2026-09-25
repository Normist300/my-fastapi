from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    postgres_dsn: str


@lru_cache
def get_settings() -> Settings:
    return Settings() # type: ignore


engine: AsyncEngine = create_async_engine(
    get_settings().postgres_dsn,
    pool_pre_ping=True, # это общая рекомендация SQLAlchemy для прода
)

async_session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine,
    expire_on_commit=False, # официальная рекомендация именно для async-сессий
)