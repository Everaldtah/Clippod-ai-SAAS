"""Video routes."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.schemas.video import (
    VideoCreate, VideoUpdate, VideoResponse, VideoUploadResponse,
    VideoListResponse, TranscriptionResponse
)
from app.services.video import VideoService
from app.services.storage import StorageService
from app.models.user import User

router = APIRouter(prefix="/videos", tags=["Videos"])


@router.get("", response_model=VideoListResponse)
async def list_videos(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    project_id: Optional[str] = None,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List user's videos."""
    video_service = VideoService(db)
    videos, total = await video_service.list_videos(
        user_id=current_user.id,
        page=page,
        page_size=page_size,
        project_id=project_id,
        status=status
    )
    
    # Add URLs to videos
    storage_service = StorageService()
    for video in videos:
        video.video_url = storage_service.get_public_url(video.storage_key)
    
    return VideoListResponse(
        items=videos,
        total=total,
        page=page,
        page_size=page_size
    )


@router.post("/upload-url", response_model=VideoUploadResponse)
async def get_upload_url(
    video_data: VideoCreate,
    file_size: int = Query(..., gt=0),
    file_type: str = Query(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get presigned upload URL for video."""
    # Check user can upload
    if not current_user.can_upload():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Upload limit reached. Please upgrade your plan."
        )
    
    # Validate file type
    allowed_extensions = ["mp4", "mov", "avi", "mkv", "webm", "mp3", "wav", "m4a", "flac"]
    file_ext = file_type.split("/")[-1].lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
        )
    
    # Create video record
    video_service = VideoService(db)
    video = await video_service.create(
        user_id=current_user.id,
        video_data=video_data,
        original_filename=f"upload.{file_ext}",
        file_size_bytes=file_size,
        format=file_ext
    )
    
    # Generate presigned upload URL
    storage_service = StorageService()
    upload_url, fields = await storage_service.generate_upload_url(
        key=video.storage_key,
        content_type=file_type,
        size=file_size
    )
    
    return VideoUploadResponse(
        video_id=video.id,
        upload_url=upload_url,
        fields=fields
    )


@router.post("/upload", response_model=VideoResponse)
async def upload_video(
    title: str,
    file: UploadFile = File(...),
    description: Optional[str] = None,
    project_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Upload video directly (for small files)."""
    # Check user can upload
    if not current_user.can_upload():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Upload limit reached. Please upgrade your plan."
        )
    
    # Validate file type
    allowed_types = ["video/mp4", "video/quicktime", "video/x-msvideo", "video/x-matroska", "video/webm"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_types)}"
        )
    
    # Create video record and upload
    video_service = VideoService(db)
    storage_service = StorageService()
    
    video = await video_service.upload_video(
        user_id=current_user.id,
        file=file,
        title=title,
        description=description,
        project_id=project_id,
        storage_service=storage_service
    )
    
    # Add URL
    video.video_url = storage_service.get_public_url(video.storage_key)
    
    return video


@router.get("/{video_id}", response_model=VideoResponse)
async def get_video(
    video_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get video details."""
    video_service = VideoService(db)
    video = await video_service.get_by_id(video_id)
    
    if not video or video.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )
    
    # Add URL
    storage_service = StorageService()
    video.video_url = storage_service.get_public_url(video.storage_key)
    
    return video


@router.patch("/{video_id}", response_model=VideoResponse)
async def update_video(
    video_id: str,
    video_data: VideoUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update video details."""
    video_service = VideoService(db)
    video = await video_service.get_by_id(video_id)
    
    if not video or video.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )
    
    updated_video = await video_service.update(video_id, video_data)
    
    # Add URL
    storage_service = StorageService()
    updated_video.video_url = storage_service.get_public_url(updated_video.storage_key)
    
    return updated_video


@router.delete("/{video_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_video(
    video_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete video."""
    video_service = VideoService(db)
    video = await video_service.get_by_id(video_id)
    
    if not video or video.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )
    
    # Delete from storage
    storage_service = StorageService()
    await storage_service.delete_file(video.storage_key)
    
    # Delete clips
    for clip in video.clips:
        if clip.storage_key:
            await storage_service.delete_file(clip.storage_key)
        if clip.thumbnail_key:
            await storage_service.delete_file(clip.thumbnail_key)
    
    # Delete record
    await video_service.delete(video_id)
    
    return None


@router.post("/{video_id}/process")
async def process_video(
    video_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Start video processing (transcription + analysis)."""
    video_service = VideoService(db)
    video = await video_service.get_by_id(video_id)
    
    if not video or video.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )
    
    if video.is_processing():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Video is already being processed"
        )
    
    # Start processing
    await video_service.start_processing(video_id)
    
    return {"message": "Video processing started", "video_id": video_id}


@router.get("/{video_id}/transcription", response_model=TranscriptionResponse)
async def get_transcription(
    video_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get video transcription."""
    video_service = VideoService(db)
    video = await video_service.get_by_id(video_id)
    
    if not video or video.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )
    
    if not video.transcription:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Transcription not available yet"
        )
    
    return TranscriptionResponse(
        video_id=video_id,
        text=video.transcription_text or "",
        language=video.language,
        segments=video.transcription.get("segments", []),
        duration=video.duration_seconds or 0
    )
