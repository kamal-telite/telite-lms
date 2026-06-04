import os
import uuid
from typing import Set
from fastapi import UploadFile, HTTPException, status

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "uploads", "branding")
ALLOWED_EXTENSIONS: Set[str] = {"png", "jpeg", "jpg", "svg", "ico"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

def get_file_extension(filename: str) -> str:
    if "." not in filename:
        return ""
    return filename.rsplit(".", 1)[1].lower()

async def save_branding_asset(file: UploadFile, org_slug: str, asset_type: str) -> str:
    """
    Save an uploaded branding asset (logo, favicon, banner) securely.
    Returns the public URL path for the saved file.
    """
    # 1. Validate extension
    ext = get_file_extension(file.filename or "")
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # 2. Check file size (by reading content into memory and checking length)
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File too large. Maximum size is 5MB."
        )
    
    # 3. Ensure upload directory exists
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    # 4. Generate secure filename to prevent path traversal
    # Format: {org_slug}-{asset_type}-{uuid}.{ext}
    safe_slug = "".join(c for c in org_slug if c.isalnum() or c in "-_")
    unique_id = uuid.uuid4().hex[:8]
    filename = f"{safe_slug}-{asset_type}-{unique_id}.{ext}"
    
    file_path = os.path.join(UPLOAD_DIR, filename)

    # 5. Save file
    with open(file_path, "wb") as f:
        f.write(content)

    # Return the public URL path (assuming /uploads is mounted statically in main.py)
    return f"/uploads/branding/{filename}"
