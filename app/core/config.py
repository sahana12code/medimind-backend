from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ========================
    # APP SETTINGS
    # ========================
    app_name: str = "MediMind API"
    secret_key: str = "change-this-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7

    # ========================
    # DATABASE
    # ========================
    database_url: str = "sqlite:///./medimind.db"

    # ========================
    # CORS
    # ========================
    cors_origins: list[str] = ["*"]

    # ========================
    # REMINDER SETTINGS
    # ========================
    reminder_grace_minutes: int = 30  # after how many minutes reminder becomes missed

    # ========================
    # SCHEDULER SETTINGS (NEW)
    # ========================
    scheduler_enabled: bool = True
    scheduler_interval_minutes: int = 1  # how often background job runs

    # ========================
    # TWILIO SMS SETTINGS
    # ========================
    twilio_enabled: bool = False
    twilio_account_sid: str | None = None
    twilio_auth_token: str | None = None
    twilio_from_number: str | None = None

    # ========================
    # SMTP (OPTIONAL FALLBACK)
    # ========================
    smtp_enabled: bool = False
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from_email: str | None = None
    smtp_use_tls: bool = True

    # ========================
    # MODEL CONFIG
    # ========================
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()