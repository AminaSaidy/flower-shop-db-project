from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str
    ES_URL: str = "http://elasticsearch:9200"
    ES_INDEX: str = "products"
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    ENVIRONMENT: str = "development"
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_WEB_APP_URL: str = ""

    class Config:
        env_file = ".env"

settings = Settings()