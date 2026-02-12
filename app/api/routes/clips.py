"""Clip routes."""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.schemas.clip import (
    ClipCreate, ClipUpdate, ClipResponse, ClipListResponse,
    ClipRenderRequest, AutoGenerateClipsRequest, AutoGenerateClipsResponse
)
from app.services.clip import ClipService
from app.services.video import VideoService
from app.services.storage import StorageService
from app.models.user import User

router = APIRouter(prefix="/clips", tags=["Clips"])


@router.get("", response_model=ClipListResponse)
async def list_clips(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    video_id: Optional[str] = None,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List user's clips."""
    clip_service = ClipService(db)
    clips, total = await clip_service.list_clips(
        user_id=current_user.id,
        page=page,
        page_size=page_size,
        video_id=video_id,
        status=status
    )
    
    # Add URLs to clips
    storage_service = StorageService()
    for clip in clips:
        if clip.storage_key:
            clip.clip_url = storage_service.get_public_url(clip.storage_key)
        if clip.thumbnail_key:
            clip.thumbnail_url = storage_service.get_public_url(clip.thumbnail_key)
    
    return ClipListResponse(
        items=clips,
        total=total,
        page=page,
        page_size=page_size
    )


@router.post("/auto-generate", response_model=AutoGenerateClipsResponse)
async def auto_generate_clips(
    request: AutoGenerateClipsRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Auto-generate clips from video using AI."""
    # Check user can render
    if not current_user.can_render():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Render credits exhausted. Please upgrade your plan."
        )
    
    # Verify video exists and belongs to user
    video_service = VideoService(db)
    video = await video_service.get_by_id(request.video_id)
    
    if not video or video.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )
    
    if not video.transcription:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Video must be transcribed first"
        )
    
    # Generate clips
    clip_service = ClipService(db)
    clips = await clip_service.auto_generate_clips(
        video_id=request.video_id,
        user_id=current_user.id,
        max_clips=request.max_clips,
        min_duration=request.min_duration,
        max_duration=request.max_duration
    )
    
    return AutoGenerateClipsResponse(
        video_id=request.video_id,
        clips_generated=len(clips),
        clip_ids=[clip.id for clip in clips],
        estimated_completion_time=len(clips) * 60  # ~1 min per clip
    )


@router.post("/manual", response_model=ClipResponse)
async def create_manual_clip(
    clip_data: ClipCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a manual clip with custom timing."""
    # Check user can render
    if not current_user.can_render():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Render credits exhausted. Please upgrade your plan."
        )
    
    # Verify video exists and belongs to user
    video_service = VideoService(db)
    video = await video_service.get_by_id(clip_data.video_id)
    
    if not video or video.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )
    
    # Validate timing
    if clip_data.start_time >= clip_data.end_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Start time must be before end time"
        )
    
    duration = clip_data.end_time - clip_data.start_time
    if duration < 5 or duration > 180:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Clip duration must be between 5 and 180 seconds"
        )
    
    # Create clip
    clip_service = ClipService(db)
    clip = await clip_service.create(
        user_id=current_user.id,
        clip_data=clip_data
    )
    
    return clip


@router.get("/{clip_id}", response_model=ClipResponse)
async def get_clip(
    clip_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get clip details."""
    clip_service = ClipService(db)
    clip = await clip_service.get_by_id(clip_id)
    
    if not clip or clip.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Clip not found"
        )
    
    # Add URLs
    storage_service = StorageService()
    if clip.storage_key:
        clip.clip_url = storage_service.get_public_url(clip.storage_key)
    if clip.thumbnail_key:
        clip.thumbnail_url = storage_service.get_public_url(clip.thumbnail_key)
    
    return clip


@router.patch("/{clip_id}", response_model=ClipResponse)
async def update_clip(
    clip_id: str,
    clip_data: ClipUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update clip details."""
    clip_service = ClipService(db)
    clip = await clip_service.get_by_id(clip_id)
    
    if not clip or clip.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Clip not found"
        )
    
    updated_clip = await clip_service.update(clip_id, clip_data)
    
    # Add URLs
    storage_service = StorageService()
    if updated_clip.storage_key:
        updated_clip.clip_url = storage_service.get_public_url(updated_clip.storage_key)
    if updated_clip.thumbnail_key:
        updated_clip.thumbnail_url = storage_service.get_public_url(updated_clip.thumbnail_key)
    
    return updated_clip


@router.post("/{clip_id}/render", response_model=ClipResponse)
async def render_clip(
    clip_id: str,
    render_options: ClipRenderRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Start rendering a clip."""
    # Check user can render
    if not current_user.can_render():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Render credits exhausted. Please upgrade your plan."
        )
    
    clip_service = ClipService(db)
    clip = await clip_service.get_by_id(clip_id)
    
    if not clip or clip.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Clip not found"
        )
    
    if clip.status == "rendering":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Clip is already being rendered"
        )
    
    # Start rendering
    await clip_service.start_render(clip_id, render_options)
    
    # Update clip with render options
    updated_clip = await clip_service.get_by_id(clip_id)
    
    return updated_clip


@router.delete("/{clip_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_clip(
    clip_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete clip."""
    clip_service = ClipService(db)
    clip = await clip_service.get_by_id(clip_id)
    
    if not clip or clip.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Clip not found"
        )
    
    # Delete from storage
    storage_service = StorageService()
    if clip.storage_key:
        await storage_service.delete_file(clip.storage_key)
    if clip.thumbnail_key:
        await storage_service.delete_file(clip.thumbnail_key)
    
    # Delete record
    await clip_service.delete(clip_id)
    
    return None


@router.get("/{clip_id}/download")
async def download_clip(
    clip_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get download URL for clip."""
    clip_service = ClipService(db)
    clip = await clip_service.get_by_id(clip_id)
    
    if not clip or clip.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Clip not found"
        )
    
    if clip.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Clip is not ready for download"
        )
    
    # Generate download URL
    storage_service = StorageService()
    download_url = await storage_service.generate_download_url(
        clip.storage_key,
        filename=f"{clip.title}.mp4"
    )
    
    return {"download_url": download_url}
