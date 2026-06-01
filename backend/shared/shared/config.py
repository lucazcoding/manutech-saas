from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class SharedSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = ""
    redis_url: str = "redis://localhost:6379/0"
    redis_password: str = ""
    jwt_public_key: str = ""
    environment: str = "development"
    supabase_url: str = ""
    supabase_service_key: str = ""
    storage_bucket: str = "attachments"


@lru_cache
def get_shared_settings() -> SharedSettings:
    return SharedSettings()
