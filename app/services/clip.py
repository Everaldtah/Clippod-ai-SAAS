"""Clip service."""
from datetime import datetime
from typing import Optional, Tuple, List, Dict, Any
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.clip import Clip, ClipStatus
from app.models.video import Video
from app.schemas.clip import ClipCreate, ClipUpdate, ClipRenderRequest
from app.services.video import VideoService
from app.services.user import UserService
from app.workers.tasks import render_clip_task
from app.core.config import settings


class ClipService:
    """Clip service for clip management."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_id(self, clip_id: str) -> Optional[Clip]:
        """Get clip by ID."""
        result = await self.db.execute(
            select(Clip).where(Clip.id == clip_id)
        )
        return result.scalar_one_or_none()
    
    async def list_clips(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
        video_id: Optional[str] = None,
        status: Optional[str] = None
    ) -> Tuple[List[Clip], int]:
        """List user's clips with pagination."""
        query = select(Clip).where(Clip.user_id == user_id)
        
        if video_id:
            query = query.where(Clip.video_id == video_id)
        
        if status:
            query = query.where(Clip.status == status)
        
        # Get total count
        count_query = select(func.count(Clip.id)).where(Clip.user_id == user_id)
        if video_id:
            count_query = count_query.where(Clip.video_id == video_id)
        if status:
            count_query = count_query.where(Clip.status == status)
        
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0
        
        # Get paginated results
        query = query.order_by(desc(Clip.created_at))
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        result = await self.db.execute(query)
        clips = result.scalars().all()
        
        return list(clips), total
    
    async def create(
        self,
        user_id: str,
        clip_data: ClipCreate
    ) -> Clip:
        """Create a new clip."""
        duration = clip_data.end_time - clip_data.start_time
        
        clip = Clip(
            video_id=clip_data.video_id,
            user_id=user_id,
            title=clip_data.title,
            description=clip_data.description,
            start_time=clip_data.start_time,
            end_time=clip_data.end_time,
            duration_seconds=duration,
            status=ClipStatus.PENDING,
            progress_percent=0,
            viral_score=clip_data.viral_score,
            hook_score=clip_data.hook_score,
            engagement_score=clip_data.engagement_score,
            keywords=clip_data.keywords or [],
            topics=clip_data.topics or [],
            transcript_segment=clip_data.transcript_segment,
            style_preset="modern",
            subtitle_enabled=True,
            emoji_enabled=True,
            zoom_enabled=True,
            face_tracking_enabled=True,
            background_blur=False,
            published_platforms=[]
        )
        
        self.db.add(clip)
        await self.db.commit()
        await self.db.refresh(clip)
        
        return clip
    
    async def auto_generate_clips(
        self,
        video_id: str,
        user_id: str,
        max_clips: int = 5,
        min_duration: int = 15,
        max_duration: int = 60
    ) -> List[Clip]:
        """Auto-generate clips from video using AI analysis."""
        video_service = VideoService(self.db)
        video = await video_service.get_by_id(video_id)
        
        if not video or not video.analysis_results:
            raise ValueError("Video analysis not available")
        
        # Get highlights from analysis
        highlights = video.analysis_results.get("highlights", [])
        
        clips = []
        for i, highlight in enumerate(highlights[:max_clips]):
            start_time = highlight.get("start", 0)
            end_time = highlight.get("end", start_time + 30)
            duration = end_time - start_time
            
            # Adjust duration if needed
            if duration < min_duration:
                end_time = start_time + min_duration
            elif duration > max_duration:
                end_time = start_time + max_duration
            
            clip_data = ClipCreate(
                title=f"Clip {i+1}: {highlight.get('title', 'Untitled')}",
                video_id=video_id,
                start_time=start_time,
                end_time=end_time,
                description=highlight.get("description", ""),
                viral_score=highlight.get("viral_score"),
                hook_score=highlight.get("hook_score"),
                engagement_score=highlight.get("engagement_score"),
                keywords=highlight.get("keywords", []),
                topics=highlight.get("topics", []),
                transcript_segment=highlight.get("transcript", "")
            )
            
            clip = await self.create(user_id, clip_data)
            clips.append(clip)
        
        return clips
    
    async def update(self, clip_id: str, clip_data: ClipUpdate) -> Clip:
        """Update clip details."""
        clip = await self.get_by_id(clip_id)
        if not clip:
            raise ValueError("Clip not found")
        
        update_data = clip_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(clip, field, value)
        
        await self.db.commit()
        await self.db.refresh(clip)
        
        return clip
    
    async def delete(self, clip_id: str) -> None:
        """Delete clip."""
        clip = await self.get_by_id(clip_id)
        if clip:
            await self.db.delete(clip)
            await self.db.commit()
    
    async def start_render(
        self,
        clip_id: str,
        render_options: ClipRenderRequest
    ) -> None:
        """Start clip rendering."""
        clip = await self.get_by_id(clip_id)
        if not clip:
            raise ValueError("Clip not found")
        
        # Update render options
        clip.style_preset = render_options.style_preset
        clip.subtitle_enabled = render_options.subtitle_enabled
        clip.subtitle_style = render_options.subtitle_style
        clip.emoji_enabled = render_options.emoji_enabled
        clip.zoom_enabled = render_options.zoom_enabled
        clip.face_tracking_enabled = render_options.face_tracking_enabled
        clip.background_blur = render_options.background_blur
        
        clip.status = ClipStatus.QUEUED
        clip.progress_percent = 0
        await self.db.commit()
        
        # Queue render task
        render_clip_task.delay(clip_id)
    
    async def update_status(
        self,
        clip_id: str,
        status: ClipStatus,
        progress_percent: Optional[int] = None,
        error_message: Optional[str] = None
    ) -> None:
        """Update clip rendering status."""
        clip = await self.get_by_id(clip_id)
        if clip:
            clip.status = status
            if progress_percent is not None:
                clip.progress_percent = progress_percent
            if error_message:
                clip.error_message = error_message
            await self.db.commit()
    
    async def complete_render(
        self,
        clip_id: str,
        storage_key: str,
        file_size_bytes: int,
        thumbnail_key: Optional[str] = None
    ) -> None:
        """Mark clip rendering as complete."""
        clip = await self.get_by_id(clip_id)
        if clip:
            clip.status = ClipStatus.COMPLETED
            clip.storage_key = storage_key
            clip.file_size_bytes = file_size_bytes
            clip.thumbnail_key = thumbnail_key
            clip.progress_percent = 100
            clip.rendered_at = datetime.utcnow()
            await self.db.commit()
            
            # Increment user's clips generated count
            user_service = UserService(self.db)
            await user_service.increment_clips_generated(clip.user_id)
    
    async def fail_render(self, clip_id: str, error: str) -> None:
        """Mark clip rendering as failed."""
        clip = await self.get_by_id(clip_id)
        if clip:
            clip.status = ClipStatus.FAILED
            clip.error_message = error
            await self.db.commit()
