"""Project model for organizing videos."""
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlalchemy import String, DateTime, JSON, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Project(Base):
    """Project model for organizing videos."""
    
    __tablename__ = "projects"
    
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Basic info
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Settings
    settings: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, default=dict)
    
    # Branding (for agency/white-label)
    brand_color: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)
    logo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    watermark_enabled: Mapped[bool] = mapped_column(default=True, nullable=False)
    custom_watermark_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
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
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="projects")
    videos: Mapped[List["Video"]] = relationship("Video", back_populates="project", lazy="selectin")
    
    def __repr__(self) -> str:
        return f"<Project {self.name}>"
    
    def get_videos_count(self) -> int:
        """Get number of videos in project."""
        return len(self.videos)
    
    def get_clips_count(self) -> int:
        """Get total number of clips from all videos."""
        return sum(len(video.clips) for video in self.videos)
