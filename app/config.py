from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Multi Vendor Fetch Service"
    env: str = "local"

    APP_SERVICE_URL: str = ""
    RabbitMQ_URL: str = ""
    MONGO_URL: str = ""
    MOCK_VENDOR_URL: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        if self.env == "local":
            self.APP_SERVICE_URL = "http://localhost:8000/"
            self.RabbitMQ_URL = "amqp://localhost/"
            self.MONGO_URL = "mongodb://admin:admin@localhost:27017/"
            self.MOCK_VENDOR_URL = "http://localhost:80"
        else:
            self.APP_SERVICE_URL = "http://app/"
            self.RabbitMQ_URL = "amqp://guest:guest@rabbitmq:5672/"
            self.MONGO_URL = "mongodb://admin:admin@mongo:27017/"
            self.MOCK_VENDOR_URL = "http://mock-vendor"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
