"""Video service."""
import os
import uuid
from datetime import datetime
from typing import Optional, Tuple, List, Dict, Any
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.video import Video, VideoStatus
from app.models.user import User
from app.schemas.video import VideoCreate, VideoUpdate
from app.services.storage import StorageService
from app.services.user import UserService
from app.core.config import settings
from app.workers.tasks import process_video_task


class VideoService:
    """Video service for video management."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_id(self, video_id: str) -> Optional[Video]:
        """Get video by ID."""
        result = await self.db.execute(
            select(Video).where(Video.id == video_id)
        )
        return result.scalar_one_or_none()
    
    async def list_videos(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
        project_id: Optional[str] = None,
        status: Optional[str] = None
    ) -> Tuple[List[Video], int]:
        """List user's videos with pagination."""
        query = select(Video).where(Video.user_id == user_id)
        
        if project_id:
            query = query.where(Video.project_id == project_id)
        
        if status:
            query = query.where(Video.status == status)
        
        # Get total count
        count_query = select(func.count(Video.id)).where(Video.user_id == user_id)
        if project_id:
            count_query = count_query.where(Video.project_id == project_id)
        if status:
            count_query = count_query.where(Video.status == status)
        
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0
        
        # Get paginated results
        query = query.order_by(desc(Video.created_at))
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        result = await self.db.execute(query)
        videos = result.scalars().all()
        
        return list(videos), total
    
    async def create(
        self,
        user_id: str,
        video_data: VideoCreate,
        original_filename: str,
        file_size_bytes: int,
        format: str
    ) -> Video:
        """Create a new video record."""
        # Generate storage key
        storage_key = f"videos/{user_id}/{str(uuid.uuid4())}.{format}"
        
        video = Video(
            user_id=user_id,
            project_id=video_data.project_id,
            title=video_data.title,
            description=video_data.description,
            original_filename=original_filename,
            storage_key=storage_key,
            file_size_bytes=file_size_bytes,
            format=format,
            status=VideoStatus.PENDING,
            progress_percent=0,
            source_url=video_data.source_url
        )
        
        self.db.add(video)
        await self.db.commit()
        await self.db.refresh(video)
        
        return video
    
    async def upload_video(
        self,
        user_id: str,
        file,
        title: str,
        description: Optional[str] = None,
        project_id: Optional[str] = None,
        storage_service: Optional[StorageService] = None
    ) -> Video:
        """Upload video and create record."""
        if storage_service is None:
            storage_service = StorageService()
        
        # Get file info
        file_size = 0
        content = await file.read()
        file_size = len(content)
        
        # Get extension from filename
        filename = file.filename or "video.mp4"
        extension = filename.split(".")[-1].lower()
        
        # Create video record
        video_data = VideoCreate(
            title=title,
            description=description,
            project_id=project_id
        )
        
        video = await self.create(
            user_id=user_id,
            video_data=video_data,
            original_filename=filename,
            file_size_bytes=file_size,
            format=extension
        )
        
        # Upload to storage
        await storage_service.upload_file(
            file_content=content,
            key=video.storage_key,
            content_type=file.content_type or f"video/{extension}"
        )
        
        # Update status
        video.status = VideoStatus.UPLOADED
        video.progress_percent = 100
        await self.db.commit()
        
        # Increment user's upload count
        user_service = UserService(self.db)
        await user_service.increment_uploads(user_id)
        
        # Start processing in background
        process_video_task.delay(video.id)
        
        return video
    
    async def update(self, video_id: str, video_data: VideoUpdate) -> Video:
        """Update video details."""
        video = await self.get_by_id(video_id)
        if not video:
            raise ValueError("Video not found")
        
        update_data = video_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(video, field, value)
        
        await self.db.commit()
        await self.db.refresh(video)
        
        return video
    
    async def delete(self, video_id: str) -> None:
        """Delete video."""
        video = await self.get_by_id(video_id)
        if video:
            await self.db.delete(video)
            await self.db.commit()
    
    async def update_status(
        self,
        video_id: str,
        status: VideoStatus,
        progress_percent: Optional[int] = None,
        error_message: Optional[str] = None
    ) -> None:
        """Update video processing status."""
        video = await self.get_by_id(video_id)
        if video:
            video.status = status
            if progress_percent is not None:
                video.progress_percent = progress_percent
            if error_message:
                video.error_message = error_message
            await self.db.commit()
    
    async def update_transcription(
        self,
        video_id: str,
        transcription: Dict[str, Any],
        transcription_text: str,
        language: Optional[str] = None
    ) -> None:
        """Update video transcription."""
        video = await self.get_by_id(video_id)
        if video:
            video.transcription = transcription
            video.transcription_text = transcription_text
            video.language = language
            video.status = VideoStatus.TRANSCRIBED
            await self.db.commit()
    
    async def update_analysis(
        self,
        video_id: str,
        analysis_results: Dict[str, Any]
    ) -> None:
        """Update video analysis results."""
        video = await self.get_by_id(video_id)
        if video:
            video.analysis_results = analysis_results
            video.status = VideoStatus.ANALYZED
            await self.db.commit()
    
    async def start_processing(self, video_id: str) -> None:
        """Start video processing."""
        video = await self.get_by_id(video_id)
        if not video:
            raise ValueError("Video not found")
        
        # Update status
        video.status = VideoStatus.PROCESSING
        video.progress_percent = 0
        await self.db.commit()
        
        # Queue processing task
        process_video_task.delay(video_id)
    
    async def complete_processing(self, video_id: str) -> None:
        """Mark video processing as complete."""
        video = await self.get_by_id(video_id)
        if video:
            video.status = VideoStatus.COMPLETED
            video.progress_percent = 100
            video.processed_at = datetime.utcnow()
            await self.db.commit()
    
    async def fail_processing(self, video_id: str, error: str) -> None:
        """Mark video processing as failed."""
        video = await self.get_by_id(video_id)
        if video:
            video.status = VideoStatus.FAILED
            video.error_message = error
            await self.db.commit()
