"""Storage service for file operations - Local filesystem version for shared hosting."""
import os
import uuid
import shutil
from typing import Optional, Tuple
from pathlib import Path

from app.core.config import settings


class StorageService:
    """Storage service for local filesystem operations."""

    def __init__(self):
        self.storage_path = Path(settings.STORAGE_PATH)
        self.public_url = settings.STORAGE_PUBLIC_URL

        # Create storage directories
        self.storage_path.mkdir(parents=True, exist_ok=True)
        (self.storage_path / "videos").mkdir(parents=True, exist_ok=True)
        (self.storage_path / "clips").mkdir(parents=True, exist_ok=True)
        (self.storage_path / "thumbnails").mkdir(parents=True, exist_ok=True)
        (self.storage_path / "avatars").mkdir(parents=True, exist_ok=True)
        (self.storage_path / "temp").mkdir(parents=True, exist_ok=True)

    def get_public_url(self, key: str) -> str:
        """Get public URL for a file."""
        return f"{self.public_url}/{key}"

    def _generate_key(self, prefix: str, extension: str) -> str:
        """Generate a unique storage key."""
        unique_id = str(uuid.uuid4())
        return f"{prefix}/{unique_id}.{extension}"

    async def upload_file(
        self,
        file_content: bytes,
        key: str,
        content_type: str = "application/octet-stream"
    ) -> str:
        """Upload file to storage."""
        file_path = self.storage_path / key
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, "wb") as f:
            f.write(file_content)

        return key

    async def upload_video(
        self,
        file_obj,
        user_id: str,
        extension: str = "mp4"
    ) -> str:
        """Upload video file."""
        filename = str(uuid.uuid4())
        key = f"videos/{user_id}/{filename}.{extension}"
        file_path = self.storage_path / key

        # Create directory
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Save file
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file_obj, f)

        return key

    async def upload_avatar(
        self,
        file_obj,
        user_id: str
    ) -> str:
        """Upload user avatar."""
        # Get extension from filename
        filename = file_obj.filename or "avatar.jpg"
        extension = filename.split(".")[-1].lower()
        if extension not in ["jpg", "jpeg", "png", "webp"]:
            extension = "jpg"

        key = f"avatars/{user_id}.{extension}"
        file_path = self.storage_path / key

        # Save file
        content = await file_obj.read()
        with open(file_path, "wb") as f:
            f.write(content)

        return key

    async def upload_clip(
        self,
        file_path: str,
        user_id: str,
        clip_id: str
    ) -> str:
        """Upload rendered clip."""
        key = f"clips/{user_id}/{clip_id}.mp4"
        dest_path = self.storage_path / key

        # Create directory
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        # Copy file
        shutil.copy(file_path, dest_path)

        return key

    async def upload_thumbnail(
        self,
        file_path: str,
        user_id: str,
        clip_id: str
    ) -> str:
        """Upload clip thumbnail."""
        key = f"thumbnails/{user_id}/{clip_id}.jpg"
        dest_path = self.storage_path / key

        # Create directory
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        # Copy file
        shutil.copy(file_path, dest_path)

        return key

    async def generate_upload_url(
        self,
        key: str,
        content_type: str,
        size: int,
        expiration: int = 3600
    ) -> Tuple[str, Optional[dict]]:
        """Generate upload info (returns URL as None for local storage)."""
        # For local storage, we'll use direct upload via POST
        # Return the key that should be used
        return None, {"key": key, "use_direct_upload": True}

    async def generate_download_url(
        self,
        key: str,
        filename: Optional[str] = None,
        expiration: int = 3600
    ) -> str:
        """Generate download URL."""
        return f"{self.public_url}/{key}"

    async def delete_file(self, key: str) -> bool:
        """Delete file from storage."""
        try:
            file_path = self.storage_path / key
            if file_path.exists():
                file_path.unlink()
            return True
        except Exception:
            return False

    async def file_exists(self, key: str) -> bool:
        """Check if file exists in storage."""
        file_path = self.storage_path / key
        return file_path.exists()

    async def download_file(self, key: str, local_path: str) -> bool:
        """Download file from storage to local path."""
        try:
            file_path = self.storage_path / key
            shutil.copy(file_path, local_path)
            return True
        except Exception as e:
            print(f"Failed to download file: {str(e)}")
            return False

    def get_local_path(self, key: str) -> Path:
        """Get local filesystem path for a storage key."""
        return self.storage_path / key
