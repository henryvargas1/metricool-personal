import os
from pathlib import Path
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    APP_ENV: str = "development"
    PORT: int = 8000
    DATABASE_URL: str = f"sqlite:///{BASE_DIR}/data/metricool.db"
    CRON_SECRET: str = "supersecret_cron_key_cambiame"
    BASE_URL: str = "http://localhost:8000"
    
    # Uploads dir
    UPLOAD_DIR: str = str(BASE_DIR / "uploads")
    
    # YouTube API
    YOUTUBE_CLIENT_ID: str = ""
    YOUTUBE_CLIENT_SECRET: str = ""
    YOUTUBE_REDIRECT_URI: str = "http://localhost:8000/api/auth/youtube/callback"
    
    # Meta / Instagram API
    META_APP_ID: str = ""
    META_APP_SECRET: str = ""
    META_REDIRECT_URI: str = "http://localhost:8000/api/auth/meta/callback"
    
    # TikTok API
    TIKTOK_CLIENT_KEY: str = ""
    TIKTOK_CLIENT_SECRET: str = ""
    TIKTOK_REDIRECT_URI: str = "http://localhost:8000/api/auth/tiktok/callback"

    class Config:
        env_file = ".env"
        extra = "allow"

settings = Settings()
