from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    # .env
    postgres_dsn: SecretStr
    secret_key: SecretStr
    # config
    app_name: str = "my-fastapi"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    access_token_expire_minutes: int = 30


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore
