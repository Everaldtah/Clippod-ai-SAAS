"""Analytics model for tracking clip performance."""
import uuid
from datetime import datetime
from typing import Optional, Dict, Any

from sqlalchemy import String, Integer, Float, DateTime, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class ClipAnalytics(Base):
    """Analytics model for tracking clip performance."""
    
    __tablename__ = "clip_analytics"
    
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    clip_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("clips.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )
    
    # Views
    total_views: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    unique_views: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Engagement
    likes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    comments: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    shares: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    saves: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Retention
    avg_watch_time_seconds: Mapped[float] = mapped_column(default=0.0, nullable=False)
    completion_rate: Mapped[float] = mapped_column(default=0.0, nullable=False)  # 0-100
    
    # Platform-specific metrics
    platform_metrics: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, default=dict)
    # Example: {
    #   "tiktok": {"views": 1000, "likes": 50, "shares": 10},
    #   "youtube": {"views": 500, "likes": 30, "comments": 5},
    #   "instagram": {"views": 800, "likes": 40, "saves": 15}
    # }
    
    # Demographics (if available)
    demographics: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    
    # Revenue tracking
    estimated_revenue: Mapped[float] = mapped_column(default=0.0, nullable=False)
    revenue_currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    
    # Viral tracking
    viral_score_current: Mapped[float] = mapped_column(default=0.0, nullable=False)
    viral_momentum: Mapped[float] = mapped_column(default=0.0, nullable=False)  # Rate of growth
    trending_hashtags: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    
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
    last_synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    clip: Mapped["Clip"] = relationship("Clip", back_populates="analytics")
    
    def __repr__(self) -> str:
        return f"<ClipAnalytics clip_id={self.clip_id} views={self.total_views}>"
    
    def get_engagement_rate(self) -> float:
        """Calculate engagement rate."""
        if self.total_views == 0:
            return 0.0
        engagements = self.likes + self.comments + self.shares + self.saves
        return (engagements / self.total_views) * 100
    
    def get_ctr(self) -> float:
        """Get click-through rate (if applicable)."""
        # Placeholder for future implementation
        return 0.0
    
    def update_viral_score(self):
        """Update viral score based on metrics."""
        # Simple algorithm - can be refined
        view_score = min(self.total_views / 10000, 40)  # Max 40 points
        engagement_score = min(self.get_engagement_rate() * 2, 30)  # Max 30 points
        retention_score = min(self.completion_rate * 0.3, 30)  # Max 30 points
        
        self.viral_score_current = view_score + engagement_score + retention_score
