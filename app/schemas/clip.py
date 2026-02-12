"""Clip schemas."""
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict

from app.models.clip import ClipStatus


class ClipBase(BaseModel):
    """Base clip schema."""
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None


class ClipCreate(ClipBase):
    """Clip creation schema."""
    video_id: str
    start_time: float = Field(..., ge=0)
    end_time: float = Field(..., gt=0)
    
    # AI-generated fields (optional, will be auto-filled if not provided)
    viral_score: Optional[float] = Field(None, ge=0, le=100)
    hook_score: Optional[float] = Field(None, ge=0, le=100)
    engagement_score: Optional[float] = Field(None, ge=0, le=100)
    keywords: Optional[List[str]] = None
    topics: Optional[List[str]] = None
    transcript_segment: Optional[str] = None
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "title": "Best Moment",
            "video_id": "vid-123",
            "start_time": 120.5,
            "end_time": 150.0,
            "description": "The most engaging part"
        }
    })


class ClipUpdate(BaseModel):
    """Clip update schema."""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    style_preset: Optional[str] = None
    subtitle_enabled: Optional[bool] = None
    emoji_enabled: Optional[bool] = None
    zoom_enabled: Optional[bool] = None
    face_tracking_enabled: Optional[bool] = None
    background_blur: Optional[bool] = None
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "title": "Updated Title",
            "subtitle_enabled": True,
            "emoji_enabled": False
        }
    })


class ClipRenderRequest(BaseModel):
    """Clip render request schema."""
    style_preset: str = Field(default="modern")
    subtitle_enabled: bool = True
    subtitle_style: Optional[Dict[str, Any]] = None
    emoji_enabled: bool = True
    zoom_enabled: bool = True
    face_tracking_enabled: bool = True
    background_blur: bool = False
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "style_preset": "modern",
            "subtitle_enabled": True,
            "emoji_enabled": True,
            "zoom_enabled": True
        }
    })


class ClipResponse(ClipBase):
    """Clip response schema."""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    video_id: str
    user_id: str
    
    # Timing
    start_time: float
    end_time: float
    duration_seconds: float
    
    # File info
    file_size_bytes: Optional[int] = None
    clip_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    
    # Status
    status: ClipStatus
    progress_percent: int
    error_message: Optional[str] = None
    
    # AI Scores
    viral_score: Optional[float] = None
    hook_score: Optional[float] = None
    engagement_score: Optional[float] = None
    sentiment_score: Optional[float] = None
    
    # Content analysis
    keywords: List[str]
    topics: List[str]
    emotions: Optional[Dict[str, Any]] = None
    transcript_segment: Optional[str] = None
    
    # Rendering settings
    style_preset: str
    subtitle_enabled: bool
    subtitle_style: Optional[Dict[str, Any]] = None
    emoji_enabled: bool
    zoom_enabled: bool
    face_tracking_enabled: bool
    background_blur: bool
    
    # Publishing
    is_published: bool
    published_at: Optional[datetime] = None
    published_platforms: List[str]
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    rendered_at: Optional[datetime] = None


class ClipListResponse(BaseModel):
    """Clip list response schema."""
    items: List[ClipResponse]
    total: int
    page: int
    page_size: int


class ClipPreviewResponse(BaseModel):
    """Clip preview response schema."""
    clip_id: str
    preview_url: str
    thumbnail_url: Optional[str] = None
    duration: float


class AutoGenerateClipsRequest(BaseModel):
    """Auto-generate clips request schema."""
    video_id: str
    max_clips: int = Field(default=5, ge=1, le=20)
    min_duration: int = Field(default=15, ge=5)
    max_duration: int = Field(default=60, ge=10)
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "video_id": "vid-123",
            "max_clips": 5,
            "min_duration": 15,
            "max_duration": 45
        }
    })


class AutoGenerateClipsResponse(BaseModel):
    """Auto-generate clips response schema."""
    video_id: str
    clips_generated: int
    clip_ids: List[str]
    estimated_completion_time: int  # seconds
