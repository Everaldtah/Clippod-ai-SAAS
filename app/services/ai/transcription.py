"""Transcription service using Whisper."""
import os
import tempfile
from typing import Optional, Dict, Any, List
import whisper

from app.core.config import settings
from app.services.storage import StorageService


class TranscriptionService:
    """Transcription service using OpenAI Whisper."""
    
    def __init__(self):
        self.model = None
        self.model_name = settings.WHISPER_MODEL
        self.device = settings.WHISPER_DEVICE
    
    def _load_model(self):
        """Lazy load the Whisper model."""
        if self.model is None:
            self.model = whisper.load_model(self.model_name).to(self.device)
        return self.model
    
    async def transcribe(
        self,
        video_id: str,
        storage_key: str,
        language: Optional[str] = None
    ) -> Dict[str, Any]:
        """Transcribe video audio."""
        # Download video to temp file
        storage_service = StorageService()
        
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            # Download from storage
            success = await storage_service.download_file(storage_key, temp_path)
            if not success:
                raise Exception("Failed to download video file")
            
            # Load model
            model = self._load_model()
            
            # Transcribe
            result = model.transcribe(
                temp_path,
                language=language,
                task="transcribe",
                verbose=False
            )
            
            # Format segments
            segments = []
            for segment in result.get("segments", []):
                segments.append({
                    "start": segment["start"],
                    "end": segment["end"],
                    "text": segment["text"].strip(),
                    "confidence": segment.get("avg_logprob", 0),
                })
            
            return {
                "text": result["text"],
                "language": result.get("language"),
                "segments": segments,
                "duration": result.get("duration", 0)
            }
        
        finally:
            # Cleanup temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    async def transcribe_with_diarization(
        self,
        video_id: str,
        storage_key: str,
        num_speakers: Optional[int] = None
    ) -> Dict[str, Any]:
        """Transcribe with speaker diarization."""
        # First get basic transcription
        result = await self.transcribe(video_id, storage_key)
        
        # TODO: Implement speaker diarization
        # This would require a separate model like pyannote.audio
        
        return result
    
    def get_word_timestamps(
        self,
        segments: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Extract word-level timestamps from segments."""
        words = []
        for segment in segments:
            text = segment.get("text", "")
            start = segment.get("start", 0)
            end = segment.get("end", 0)
            duration = end - start
            
            # Simple word-level timing (approximate)
            word_list = text.split()
            if word_list:
                word_duration = duration / len(word_list)
                for i, word in enumerate(word_list):
                    words.append({
                        "word": word,
                        "start": start + (i * word_duration),
                        "end": start + ((i + 1) * word_duration)
                    })
        
        return words
