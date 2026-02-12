"""Database configuration and session management for MySQL."""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy.pool import QueuePool

from app.core.config import settings

# Create MySQL engine
# Using pymysql driver for MySQL compatibility
mysql_url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "mysql+pymysql://")
mysql_url = mysql_url.replace("postgresql://", "mysql+pymysql://")

engine = create_engine(
    mysql_url,
    pool_size=5,  # Reduced for shared hosting
    max_overflow=5,
    pool_pre_ping=True,
    echo=settings.DEBUG,
    poolclass=QueuePool,
)

# Create session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Base class for models
Base = declarative_base()


def get_db() -> Session:
    """Dependency to get database session."""
    db = SessionLocal()
    try:
        return db
    finally:
        pass  # Don't close here, let the caller handle it


def init_db():
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)


def close_db():
    """Close database connections."""
    engine.dispose()
