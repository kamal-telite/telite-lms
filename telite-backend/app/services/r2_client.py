import os
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from fastapi import HTTPException

# Using S3 protocol for Cloudflare R2
R2_ENDPOINT = os.getenv("R2_ENDPOINT", "https://mock-r2-endpoint.cloudflare.com")
R2_ACCESS_KEY = os.getenv("R2_ACCESS_KEY", "mock-access-key")
R2_SECRET_KEY = os.getenv("R2_SECRET_KEY", "mock-secret-key")
R2_BUCKET = os.getenv("R2_BUCKET", "telite-media-bucket")

def get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=R2_ENDPOINT,
        aws_access_key_id=R2_ACCESS_KEY,
        aws_secret_access_key=R2_SECRET_KEY,
        config=Config(signature_version="s3v4"),
        region_name="auto" # R2 requires region to be 'auto' or 'us-east-1' depending on client, 'auto' is usually fine for boto3 with custom endpoint
    )

def generate_presigned_upload_url(object_key: str, mime_type: str, expiration: int = 3600) -> str:
    """Generate a presigned URL to securely upload a file to R2."""
    s3_client = get_s3_client()
    try:
        url = s3_client.generate_presigned_url(
            ClientMethod="put_object",
            Params={
                "Bucket": R2_BUCKET,
                "Key": object_key,
                "ContentType": mime_type
            },
            ExpiresIn=expiration
        )
        return url
    except ClientError as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate upload URL: {str(e)}")

def generate_presigned_download_url(object_key: str, expiration: int = 3600) -> str:
    """Generate a presigned URL to securely download/view a file from R2."""
    s3_client = get_s3_client()
    try:
        url = s3_client.generate_presigned_url(
            ClientMethod="get_object",
            Params={
                "Bucket": R2_BUCKET,
                "Key": object_key
            },
            ExpiresIn=expiration
        )
        return url
    except ClientError as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate download URL: {str(e)}")
