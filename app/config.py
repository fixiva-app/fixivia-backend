from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "fixvia-api"
    flavor: str = "dev"
    jwt_secret: str = "dev-only-change-me-use-32-bytes-min"
    jwt_hours: int = 24 * 14
    otp_ttl_minutes: int = 10
    otp_pepper: str = "dev-only-otp-pepper"
    database_url: str = "sqlite+pysqlite:///./fixvia.db"
    seed_on_start: bool = True


settings = Settings()
