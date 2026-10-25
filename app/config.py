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
    cors_origins: str = "*"
    whatsapp_enabled: bool = False
    whatsapp_api_base: str = ""
    whatsapp_api_key: str = ""
    whatsapp_sender: str = ""
    # TEMP-OTP: creds for the temporary admin OTP read API. Set real
    # values in the host console; DELETE once real SMS/WhatsApp ships.
    otp_admin_user: str = "otpadmin"
    otp_admin_pass: str = "otpadminpass"
    # R2 object storage for product images. All empty = disabled, and
    # images stay as DB blobs (local dev + test default).
    r2_endpoint: str = ""
    r2_bucket: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""


settings = Settings()
