from functools import lru_cache

from pydantic_settings import SettingsConfigDict

from shared.shared.config import SharedSettings


class OrderSettings(SharedSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    stats_cache_ttl_seconds: int = 30


@lru_cache
def get_order_settings() -> OrderSettings:
    return OrderSettings()
