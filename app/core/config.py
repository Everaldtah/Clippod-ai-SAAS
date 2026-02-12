"""Application configuration settings for shared hosting deployment."""
from functools import lru_cache
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import validator


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # App
    APP_NAME: str = "Clippod"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"
    SECRET_KEY: str = "your-super-secret-key-change-in-production"

    # API
    API_V1_PREFIX: str = "/api"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 30  # 30 days

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173", "https://clippodai.veraldlabs.co.uk", "https://www.clippodai.veraldlabs.co.uk"]

    @validator("CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    # Database - MySQL for shared hosting
    DATABASE_URL: str = "mysql+pymysql://everaldtah:Bamendaboy237$@mysql-200-149.mysql.prositehosting.net/VeraldLabsBase"
    DATABASE_POOL_SIZE: int = 5  # Reduced for shared hosting
    DATABASE_MAX_OVERFLOW: int = 5

    # Storage - Local filesystem for shared hosting
    STORAGE_TYPE: str = "local"  # local or s3
    STORAGE_PATH: str = "./storage"  # Local storage path
    STORAGE_PUBLIC_URL: str = "https://clippodai.veraldlabs.co.uk/storage"

    # S3/MinIO (optional, for future use)
    STORAGE_ENDPOINT: Optional[str] = None
    STORAGE_ACCESS_KEY: Optional[str] = None
    STORAGE_SECRET_KEY: Optional[str] = None
    STORAGE_BUCKET_NAME: Optional[str] = None
    STORAGE_REGION: str = "us-east-1"
    STORAGE_USE_SSL: bool = False

    # AI Services
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None

    # Whisper (Transcription)
    WHISPER_MODEL: str = "base"  # tiny, base, small, medium, large
    WHISPER_DEVICE: str = "cpu"  # cpu, cuda

    # Sentence Transformers
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"

    # Video Processing
    MAX_UPLOAD_SIZE_MB: int = 500  # Reduced to 500MB for shared hosting
    SUPPORTED_VIDEO_FORMATS: List[str] = ["mp4", "mov", "avi", "mkv", "webm"]
    SUPPORTED_AUDIO_FORMATS: List[str] = ["mp3", "wav", "m4a", "flac", "aac"]

    # Clip Generation
    MIN_CLIP_DURATION: int = 15  # seconds
    MAX_CLIP_DURATION: int = 60  # seconds
    TARGET_CLIP_DURATION: int = 30  # seconds
    OUTPUT_RESOLUTION: str = "1080x1920"  # 9:16 vertical

    # Stripe (Payments)
    STRIPE_SECRET_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None
    STRIPE_PRICE_ID_PRO: Optional[str] = None
    STRIPE_PRICE_ID_AGENCY: Optional[str] = None

    # Rate Limiting
    RATE_LIMIT_UPLOADS_PER_HOUR: int = 5  # Reduced for shared hosting
    RATE_LIMIT_RENDERS_PER_DAY: int = 20  # Reduced for shared hosting

    # Monitoring
    SENTRY_DSN: Optional[str] = None
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
