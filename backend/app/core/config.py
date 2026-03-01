from pydantic_settings import BaseSettings
from functools import lru_cache
import os


class Settings(BaseSettings):
    HOST: str = "0.0.0.0"
    PORT: int = 8080
    
    # Storage
    RECORDINGS_PATH: str = "/data/recordings"
    EVENTS_PATH: str = "/data/events"
    DATABASE_PATH: str = "/data/edgenvr.db"
    
    # Analytics
    DETECTION_THRESHOLD: float = 0.5
    DETECTION_INTERVAL: int = 5  # Process every Nth frame
    
    # Recording
    CONTINUOUS_FPS: int = 1
    EVENT_FPS: int = 15
    PRE_BUFFER_SECONDS: int = 5
    POST_BUFFER_SECONDS: int = 10
    
    # Security
    SECRET_KEY: str = "change-me-in-production"
    
    # Notifications
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""
    
    class Config:
        env_file = ".env"


@lru_cache()
def get_settings():
    return Settings()
