from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Multi Vendor Fetch Service"

    MONGO_URL: str = "mongodb://admin:admin@mongo:27017/"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
