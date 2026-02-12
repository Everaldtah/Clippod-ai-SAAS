"""Analytics schemas."""
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, ConfigDict


class AnalyticsResponse(BaseModel):
    """Analytics response schema."""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    clip_id: str
    
    # Views
    total_views: int
    unique_views: int
    
    # Engagement
    likes: int
    comments: int
    shares: int
    saves: int
    engagement_rate: float
    
    # Retention
    avg_watch_time_seconds: float
    completion_rate: float
    
    # Platform metrics
    platform_metrics: Dict[str, Any]
    
    # Revenue
    estimated_revenue: float
    revenue_currency: str
    
    # Viral tracking
    viral_score_current: float
    viral_momentum: float
    trending_hashtags: List[str]
    
    # Timestamps
    updated_at: datetime
    last_synced_at: Optional[datetime] = None


class AnalyticsSummary(BaseModel):
    """Analytics summary schema."""
    total_clips: int
    total_views: int
    total_likes: int
    total_comments: int
    total_shares: int
    avg_engagement_rate: float
    avg_completion_rate: float
    total_estimated_revenue: float
    top_performing_clips: List[Dict[str, Any]]


class TimeSeriesData(BaseModel):
    """Time series data point."""
    timestamp: datetime
    value: float


class AnalyticsTimeSeriesResponse(BaseModel):
    """Analytics time series response."""
    clip_id: str
    metric: str  # views, likes, engagement_rate, etc.
    data: List[TimeSeriesData]
    period: str  # day, week, month


class DashboardStatsResponse(BaseModel):
    """Dashboard stats response schema."""
    # Overview
    total_videos: int
    total_clips: int
    total_views: int
    
    # This month
    uploads_this_month: int
    clips_this_month: int
    views_this_month: int
    
    # Performance
    avg_viral_score: float
    top_clip_id: Optional[str] = None
    top_clip_title: Optional[str] = None
    top_clip_views: int
    
    # Usage
    uploads_remaining: int
    renders_remaining: int
    
    # Recent activity
    recent_clips: List[Dict[str, Any]]
