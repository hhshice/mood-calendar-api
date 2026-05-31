from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # 微信小程序
    wechat_app_id: str = ""
    wechat_app_secret: str = ""

    # 数据库
    database_url: str = "sqlite:///./mood_calendar.db"

    # JWT
    secret_key: str = "dev-secret-key"
    jwt_algorithm: str = "HS256"
    jwt_expire_days: int = 30

    # Cloudflare R2
    r2_account_id: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_bucket_name: str = "mood-calendar-images"
    r2_public_url: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
