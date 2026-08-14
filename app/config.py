from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "MB16 Showroom"
    app_env: str = "development"
    database_url: str = "sqlite:///./data/showroom.db"
    telegram_bot_token: str = ""
    admin_telegram_ids: str = ""
    debug_telegram_user_id: int | None = 1001
    debug_telegram_username: str = "demo_client"
    debug_telegram_name: str = "Demo Client"
    debug_admin_user_id: int | None = 9001
    debug_admin_username: str = "demo_admin"
    debug_admin_name: str = "Demo Admin"
    auth_max_age_seconds: int = 86400

    storage_backend: str = "local"
    upload_dir: str = "./data/uploads"
    public_base_url: str = ""
    s3_endpoint_url: str = ""
    s3_access_key_id: str = ""
    s3_secret_access_key: str = ""
    s3_bucket: str = ""
    s3_region: str = "ru-1"
    s3_public_base_url: str = ""

    max_image_mb: int = 10
    max_video_mb: int = 80

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def admin_ids(self) -> set[int]:
        ids: set[int] = set()
        for raw in self.admin_telegram_ids.split(","):
            raw = raw.strip()
            if raw:
                try:
                    ids.add(int(raw))
                except ValueError:
                    continue
        if self.app_env != "production" and self.debug_admin_user_id:
            ids.add(self.debug_admin_user_id)
        return ids

    @property
    def upload_path(self) -> Path:
        return Path(self.upload_dir).resolve()


@lru_cache
def get_settings() -> Settings:
    return Settings()
