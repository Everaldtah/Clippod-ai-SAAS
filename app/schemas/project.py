"""Project schemas."""
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict


class ProjectBase(BaseModel):
    """Base project schema."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None


class ProjectCreate(ProjectBase):
    """Project creation schema."""
    settings: Optional[Dict[str, Any]] = None
    brand_color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    logo_url: Optional[str] = None
    watermark_enabled: bool = True
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "name": "My Podcast Series",
            "description": "All episodes of my tech podcast",
            "brand_color": "#FF5733"
        }
    })


class ProjectUpdate(BaseModel):
    """Project update schema."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None
    brand_color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    logo_url: Optional[str] = None
    watermark_enabled: Optional[bool] = None
    custom_watermark_url: Optional[str] = None
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "name": "Updated Project Name",
            "brand_color": "#3366FF"
        }
    })


class ProjectResponse(ProjectBase):
    """Project response schema."""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    user_id: str
    
    # Settings
    settings: Dict[str, Any]
    
    # Branding
    brand_color: Optional[str] = None
    logo_url: Optional[str] = None
    watermark_enabled: bool
    custom_watermark_url: Optional[str] = None
    
    # Stats
    videos_count: int
    clips_count: int
    
    # Timestamps
    created_at: datetime
    updated_at: datetime


class ProjectListResponse(BaseModel):
    """Project list response schema."""
    items: List[ProjectResponse]
    total: int
    page: int
    page_size: int
