from functools import lru_cache

from pydantic_settings import SettingsConfigDict

from shared.shared.config import SharedSettings


class AuthSettings(SharedSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    jwt_private_key: str = ""
    jwt_access_token_expire_hours: int = 1
    jwt_refresh_token_expire_days: int = 7
    login_max_attempts: int = 5
    login_window_seconds: int = 900  # 15 min


@lru_cache
def get_auth_settings() -> AuthSettings:
    return AuthSettings()
