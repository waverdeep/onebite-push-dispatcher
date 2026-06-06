from functools import lru_cache
from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- environment ---
    ENV: str = "local"
    SERVICE_TZ: str = "Asia/Seoul"

    # --- database (Supabase, individual fields) ---
    DB_HOST: str
    DB_PORT: int = 6543
    DB_USER: str
    DB_PASSWORD: str = ""
    DB_NAME: str = "postgres"
    DB_SSL: bool = True
    DB_SCHEMA: str = "onebite"

    # --- auth / jwt ---
    JWT_SECRET: str = "change-me-in-prod"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_TTL_MIN: int = 15
    REFRESH_TOKEN_TTL_DAYS: int = 30

    # --- email (Resend) ---
    RESEND_API_KEY: str | None = None
    RESEND_API_BASE: str = "https://api.resend.com"
    RESEND_TIMEOUT_SEC: float = 10.0
    EMAIL_FROM: str = "onebite <noreply@example.com>"

    # --- external services (placeholders, unused in scaffold) ---
    LITELLM_API_KEY: str | None = None
    FCM_CREDENTIALS: str | None = None

    # --- Web Push (VAPID) — used by sender.deliver(). Keep in sync with the
    # server's config (same key pair from Secret Manager). ---
    VAPID_PUBLIC_KEY: str = ""
    VAPID_PRIVATE_KEY: str = ""
    VAPID_SUBJECT: str = "mailto:onebite@example.com"

    @property
    def async_dsn(self) -> str:
        """SQLAlchemy asyncpg DSN. SSL / search_path are passed via connect_args,
        not the query string (PgBouncer transaction pooler friendly)."""
        user = quote_plus(self.DB_USER)
        password = quote_plus(self.DB_PASSWORD)
        return (
            f"postgresql+asyncpg://{user}:{password}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
