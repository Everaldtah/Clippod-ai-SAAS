"""Celery tasks for background processing."""
import os
import tempfile
from celery import shared_task
from celery.exceptions import MaxRetriesExceededError

from app.workers.celery_app import celery_app
from app.services.ai.transcription import TranscriptionService
from app.services.ai.analysis import AnalysisService
from app.services.storage import StorageService
from app.services.video import VideoService
from app.services.clip import ClipService
from app.core.database import AsyncSessionLocal
from app.models.video import VideoStatus
from app.models.clip import ClipStatus


@shared_task(bind=True, max_retries=3)
def process_video_task(self, video_id: str):
    """Process video: transcribe and analyze."""
    import asyncio
    asyncio.run(_process_video_async(video_id))


async def _process_video_async(video_id: str):
    """Async helper for video processing."""
    async with AsyncSessionLocal() as db:
        video_service = VideoService(db)
        
        try:
            # Get video
            video = await video_service.get_by_id(video_id)
            if not video:
                print(f"Video {video_id} not found")
                return
            
            # Step 1: Transcription
            await video_service.update_status(
                video_id,
                VideoStatus.TRANSCRIBING,
                progress_percent=10
            )
            
            transcription_service = TranscriptionService()
            transcription = await transcription_service.transcribe(
                video_id=video_id,
                storage_key=video.storage_key
            )
            
            await video_service.update_transcription(
                video_id=video_id,
                transcription=transcription,
                transcription_text=transcription["text"],
                language=transcription.get("language")
            )
            
            # Step 2: Analysis
            await video_service.update_status(
                video_id,
                VideoStatus.ANALYZING,
                progress_percent=50
            )
            
            analysis_service = AnalysisService()
            analysis = await analysis_service.analyze_video(
                transcription=transcription,
                duration=video.duration_seconds or transcription.get("duration", 0)
            )
            
            await video_service.update_analysis(video_id, analysis)
            
            # Complete
            await video_service.complete_processing(video_id)
            
            print(f"Video {video_id} processed successfully")
            
        except Exception as exc:
            print(f"Error processing video {video_id}: {str(exc)}")
            await video_service.fail_processing(video_id, str(exc))
            raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=2)
def render_clip_task(self, clip_id: str):
    """Render clip with video processing."""
    import asyncio
    asyncio.run(_render_clip_async(clip_id))


async def _render_clip_async(clip_id: str):
    """Async helper for clip rendering."""
    async with AsyncSessionLocal() as db:
        clip_service = ClipService(db)
        video_service = VideoService(db)
        storage_service = StorageService()
        
        try:
            # Get clip
            clip = await clip_service.get_by_id(clip_id)
            if not clip:
                print(f"Clip {clip_id} not found")
                return
            
            # Get source video
            video = await video_service.get_by_id(clip.video_id)
            if not video:
                raise ValueError("Source video not found")
            
            # Update status
            await clip_service.update_status(
                clip_id,
                ClipStatus.RENDERING,
                progress_percent=10
            )
            
            # Download source video
            with tempfile.TemporaryDirectory() as temp_dir:
                source_path = os.path.join(temp_dir, "source.mp4")
                output_path = os.path.join(temp_dir, "output.mp4")
                thumbnail_path = os.path.join(temp_dir, "thumbnail.jpg")
                
                await clip_service.update_status(
                    clip_id,
                    ClipStatus.RENDERING,
                    progress_percent=20
                )
                
                # Download from storage
                success = await storage_service.download_file(
                    video.storage_key,
                    source_path
                )
                if not success:
                    raise Exception("Failed to download source video")
                
                await clip_service.update_status(
                    clip_id,
                    ClipStatus.RENDERING,
                    progress_percent=40
                )
                
                # Render clip using FFmpeg
                await _render_with_ffmpeg(
                    source_path=source_path,
                    output_path=output_path,
                    thumbnail_path=thumbnail_path,
                    start_time=clip.start_time,
                    end_time=clip.end_time,
                    subtitle_enabled=clip.subtitle_enabled,
                    style_preset=clip.style_preset
                )
                
                await clip_service.update_status(
                    clip_id,
                    ClipStatus.RENDERING,
                    progress_percent=80
                )
                
                # Upload rendered clip
                clip_key = await storage_service.upload_clip(
                    output_path,
                    clip.user_id,
                    clip.id
                )
                
                # Upload thumbnail
                thumbnail_key = None
                if os.path.exists(thumbnail_path):
                    thumbnail_key = await storage_service.upload_thumbnail(
                        thumbnail_path,
                        clip.user_id,
                        clip.id
                    )
                
                # Get file size
                file_size = os.path.getsize(output_path)
                
                # Complete
                await clip_service.complete_render(
                    clip_id,
                    storage_key=clip_key,
                    file_size_bytes=file_size,
                    thumbnail_key=thumbnail_key
                )
                
                print(f"Clip {clip_id} rendered successfully")
            
        except Exception as exc:
            print(f"Error rendering clip {clip_id}: {str(exc)}")
            await clip_service.fail_render(clip_id, str(exc))
            raise self.retry(exc=exc, countdown=60)


async def _render_with_ffmpeg(
    source_path: str,
    output_path: str,
    thumbnail_path: str,
    start_time: float,
    end_time: float,
    subtitle_enabled: bool,
    style_preset: str
):
    """Render clip using FFmpeg."""
    import ffmpeg
    
    duration = end_time - start_time
    
    # Base FFmpeg command
    stream = ffmpeg.input(source_path, ss=start_time, t=duration)
    
    # Apply vertical format (9:16) for short-form content
    # Crop to center and scale to 1080x1920
    stream = ffmpeg.filter(
        stream,
        "crop",
        "ih*9/16:ih",
        x="(iw-ih*9/16)/2"
    )
    stream = ffmpeg.filter(stream, "scale", 1080, 1920)
    
    # Add subtle zoom effect
    zoom_expr = "zoom+0.001"
    stream = ffmpeg.filter(
        stream,
        "zoompan",
        z=zoom_expr,
        d=1,
        x="iw/2-(iw/zoom/2)",
        y="ih/2-(ih/zoom/2)"
    )
    
    # Output settings for high quality
    stream = ffmpeg.output(
        stream,
        output_path,
        vcodec="libx264",
        acodec="aac",
        video_bitrate="5M",
        audio_bitrate="192k",
        pix_fmt="yuv420p",
        movflags="+faststart",
        preset="fast",
        crf=23
    )
    
    # Run FFmpeg
    ffmpeg.run(stream, overwrite_output=True, quiet=True)
    
    # Generate thumbnail at middle of clip
    thumb_time = duration / 2
    thumb_stream = ffmpeg.input(output_path, ss=thumb_time)
    thumb_stream = ffmpeg.filter(thumb_stream, "scale", 480, -1)
    thumb_stream = ffmpeg.output(thumb_stream, thumbnail_path, vframes=1)
    ffmpeg.run(thumb_stream, overwrite_output=True, quiet=True)


@shared_task
def cleanup_old_tasks():
    """Cleanup old task results and temporary files."""
    # This would clean up old task results from the result backend
    # and temporary files from the filesystem
    print("Cleanup task executed")


@shared_task
def sync_analytics():
    """Sync analytics data from social platforms."""
    # This would sync view counts, engagement metrics, etc.
    print("Analytics sync task executed")
