"""Clip model for generated short videos."""
import uuid
from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional, List, Dict, Any

from sqlalchemy import String, Integer, Float, DateTime, Enum as SQLEnum, JSON, Text, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class ClipStatus(str, PyEnum):
    """Clip generation status."""
    PENDING = "pending"
    QUEUED = "queued"
    RENDERING = "rendering"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Clip(Base):
    """Clip model for generated short videos."""
    
    __tablename__ = "clips"
    
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    video_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("videos.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Basic info
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Timing (relative to source video)
    start_time: Mapped[float] = mapped_column(Float, nullable=False)
    end_time: Mapped[float] = mapped_column(Float, nullable=False)
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    
    # File info
    storage_key: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, unique=True)
    file_size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    thumbnail_key: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Status
    status: Mapped[ClipStatus] = mapped_column(
        SQLEnum(ClipStatus),
        default=ClipStatus.PENDING,
        nullable=False,
        index=True
    )
    progress_percent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # AI Scores
    viral_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 0-100
    hook_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 0-100
    engagement_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 0-100
    sentiment_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # -1 to 1
    
    # Content analysis
    keywords: Mapped[Optional[List[str]]] = mapped_column(JSON, default=list)
    topics: Mapped[Optional[List[str]]] = mapped_column(JSON, default=list)
    emotions: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    
    # Transcript segment
    transcript_segment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Rendering settings
    style_preset: Mapped[str] = mapped_column(String(50), default="modern", nullable=False)
    subtitle_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    subtitle_style: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    emoji_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    zoom_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    face_tracking_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    background_blur: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Publishing
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    published_platforms: Mapped[Optional[List[str]]] = mapped_column(JSON, default=list)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    rendered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    video: Mapped["Video"] = relationship("Video", back_populates="clips")
    user: Mapped["User"] = relationship("User")
    analytics: Mapped[Optional["ClipAnalytics"]] = relationship("ClipAnalytics", back_populates="clip", uselist=False)
    
    def __repr__(self) -> str:
        return f"<Clip {self.title}>"
    
    def get_public_url(self, storage_public_url: str) -> Optional[str]:
        """Get public URL for the clip."""
        if not self.storage_key:
            return None
        return f"{storage_public_url}/{self.storage_key}"
    
    def get_thumbnail_url(self, storage_public_url: str) -> Optional[str]:
        """Get thumbnail URL for the clip."""
        if not self.thumbnail_key:
            return None
        return f"{storage_public_url}/{self.thumbnail_key}"
    
    def get_overall_score(self) -> float:
        """Calculate overall clip score."""
        scores = [
            self.viral_score or 0,
            self.hook_score or 0,
            self.engagement_score or 0,
        ]
        return sum(scores) / len(scores) if scores else 0
    
    def get_duration_formatted(self) -> str:
        """Get formatted duration string."""
        seconds = int(self.duration_seconds)
        return f"{seconds // 60}:{seconds % 60:02d}"
