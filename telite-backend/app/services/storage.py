import os
import uuid
import time
from pathlib import Path
from typing import Tuple

from app.core.storage_paths import media_upload_root

# Production-ready Local Disk Storage implementation
# Replaces mock S3 implementation with actual server disk storage
# API contract remains identical for backward compatibility

class StorageService:
    def __init__(self):
        self.bucket = os.getenv("STORAGE_BUCKET", "telite-media")
        self.provider = "local-disk"
        self.upload_root = media_upload_root()
        
    def generate_presigned_upload(self, filename: str, mime_type: str, org_id: int) -> Tuple[str, str]:
        """
        Generates a secure upload endpoint for direct-to-server uploads.
        Returns a tuple of (upload_url, storage_key).
        
        For local disk storage, returns the API endpoint that will handle the actual upload.
        The storage_key represents the relative path where the file will be stored.
        """
        # Ensure secure filename and path scoping by org_id
        safe_filename = "".join(c for c in filename if c.isalnum() or c in ".-_")
        unique_id = uuid.uuid4().hex[:8]
        timestamp = int(time.time())
        
        # Structure: org_{id}/media/{timestamp}_{uuid}_{filename}
        # This provides automatic multi-tenant storage isolation
        storage_key = f"org_{org_id}/media/{timestamp}_{unique_id}_{safe_filename}"
        
        # Return the API endpoint for upload (client will POST to this endpoint)
        # The actual file storage happens server-side via the upload endpoint
        upload_url = f"/api/authoring/media/upload"
        
        return upload_url, storage_key
        
    def get_public_url(self, storage_key: str) -> str:
        """
        Returns the public URL for a storage key.
        
        For local disk storage, returns the absolute URL to avoid React Router interception.
        Files are served via the /uploads static mount configured in main.py
        """
        from app.core.runtime import get_api_base_url
        base_url = get_api_base_url()
        return f"{base_url}/uploads/media/{storage_key}"
    
    def get_storage_path(self, storage_key: str) -> Path:
        """
        Returns the absolute filesystem path for a storage key.
        Used internally for actual file operations.
        """
        return (self.upload_root / storage_key).resolve()
    
    def ensure_directory(self, storage_key: str) -> None:
        """
        Ensures the directory exists for the given storage key.
        """
        target_path = self.get_storage_path(storage_key)
        target_path.parent.mkdir(parents=True, exist_ok=True)

storage_service = StorageService()
