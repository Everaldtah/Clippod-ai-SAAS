"""Video schemas."""
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict

from app.models.video import VideoStatus


class VideoBase(BaseModel):
    """Base video schema."""
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None


class VideoCreate(VideoBase):
    """Video creation schema."""
    project_id: Optional[str] = None
    source_url: Optional[str] = None
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "title": "My Podcast Episode 1",
            "description": "An interesting discussion about AI",
            "project_id": "proj-123"
        }
    })


class VideoUpdate(BaseModel):
    """Video update schema."""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    project_id: Optional[str] = None
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "title": "Updated Title",
            "description": "Updated description"
        }
    })


class VideoResponse(VideoBase):
    """Video response schema."""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    user_id: str
    project_id: Optional[str] = None
    
    # File info
    original_filename: str
    file_size_bytes: int
    duration_seconds: Optional[float] = None
    format: str
    codec: Optional[str] = None
    resolution: Optional[str] = None
    bitrate: Optional[int] = None
    fps: Optional[float] = None
    
    # Status
    status: VideoStatus
    progress_percent: int
    error_message: Optional[str] = None
    
    # Transcription
    transcription_text: Optional[str] = None
    language: Optional[str] = None
    
    # Analysis
    analysis_results: Optional[Dict[str, Any]] = None
    
    # URLs
    video_url: Optional[str] = None
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    processed_at: Optional[datetime] = None


class VideoUploadResponse(BaseModel):
    """Video upload response schema."""
    video_id: str
    upload_url: str
    fields: Optional[Dict[str, str]] = None


class VideoListResponse(BaseModel):
    """Video list response schema."""
    items: List[VideoResponse]
    total: int
    page: int
    page_size: int


class TranscriptionSegment(BaseModel):
    """Transcription segment schema."""
    start: float
    end: float
    text: str
    confidence: Optional[float] = None
    speaker: Optional[str] = None


class TranscriptionResponse(BaseModel):
    """Transcription response schema."""
    video_id: str
    text: str
    language: Optional[str] = None
    segments: List[TranscriptionSegment]
    duration: float


class VideoAnalysisResponse(BaseModel):
    """Video analysis response schema."""
    video_id: str
    status: VideoStatus
    highlights: List[Dict[str, Any]]
    topics: List[str]
    sentiment: Dict[str, Any]
    keywords: List[str]
