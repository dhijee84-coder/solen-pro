import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Environment-driven settings. Development is the default; production
    must set ENVIRONMENT=production and a strong SECRET_KEY."""

    environment: str = "development"  # development | test | production
    secret_key: str = "change-this-in-production-please"
    database_url: str = "sqlite:///./suryasetu.db"
    access_token_expire_minutes: int = 480
    algorithm: str = "HS256"

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from: str = "notifications@suryasetu.local"

    whatsapp_api_url: str = ""
    whatsapp_api_token: str = ""

    sms_api_url: str = ""
    sms_api_token: str = ""
    dev_otp: str = "1234"

    upload_dir: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
    max_upload_bytes: int = 10 * 1024 * 1024

    capacity_warning_threshold: float = 0.80
    capacity_critical_threshold: float = 0.90

    rate_limit_enabled: bool = True
    rate_limit_login: int = 8
    rate_limit_otp: int = 5
    rate_limit_contact: int = 5
    rate_limit_export: int = 10
    rate_limit_window_seconds: int = 600

    cors_origins: str = ""  # comma-separated; empty = same-origin only
    trusted_proxy: bool = False

    db_pool_size: int = 5
    db_max_overflow: int = 10

    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        extra = "ignore"

    @property
    def is_production(self) -> bool:
        return self.environment.lower() in ("production", "prod")

    @property
    def is_test(self) -> bool:
        return self.environment.lower() == "test"

    @property
    def is_debug(self) -> bool:
        return not self.is_production

    @property
    def allow_dev_otp(self) -> bool:
        """Fixed development OTP is never used in production."""
        return not self.is_production

    @property
    def expose_dev_otp(self) -> bool:
        """Never return OTP codes in API responses in production."""
        return not self.is_production

    @property
    def cookie_secure(self) -> bool:
        return self.is_production

    @property
    def cors_origin_list(self) -> list:
        if not (self.cors_origins or "").strip():
            return []
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
os.makedirs(settings.upload_dir, exist_ok=True)
os.makedirs(os.path.join(settings.upload_dir, "branding"), exist_ok=True)
