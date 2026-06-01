from functools import lru_cache

from pydantic_settings import SettingsConfigDict

from shared.shared.config import SharedSettings


class NotificationSettings(SharedSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ws_max_connections_per_user: int = 5


@lru_cache
def get_notification_settings() -> NotificationSettings:
    return NotificationSettings()
