import os
from pydantic_settings import BaseSettings
from pydantic import SecretStr
from typing import List

class Settings(BaseSettings):
    BOT_TOKEN: SecretStr
    ADMIN_IDS: List[int]
    
    GARMIN_EMAIL: str
    GARMIN_PASSWORD: str
    OPENAI_API_KEY: SecretStr
    
    # Paths
    DB_PATH: str = "sqlite+aiosqlite:///jarvisz.db"
    
    # Robust absolute path for .env to detect it irrespective of CWD
    model_config = {
        "env_file": os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore"
    }

settings = Settings()
