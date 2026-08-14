import secrets

import boto3
from fastapi import HTTPException, UploadFile

from .config import get_settings

settings = get_settings()

IMAGE_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
VIDEO_TYPES = {"video/mp4": ".mp4", "video/quicktime": ".mov", "video/webm": ".webm"}


def _safe_ext(file: UploadFile, kind: str) -> str:
    allowed = IMAGE_TYPES if kind == "image" else VIDEO_TYPES
    ext = allowed.get((file.content_type or "").lower())
    if not ext:
        raise HTTPException(status_code=400, detail=f"Unsupported {kind} format")
    return ext


def _read_limited(file: UploadFile, max_bytes: int) -> bytes:
    data = file.file.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise HTTPException(status_code=400, detail="Media file is too large")
    return data


def save_upload(file: UploadFile, kind: str) -> str:
    ext = _safe_ext(file, kind)
    max_bytes = (settings.max_image_mb if kind == "image" else settings.max_video_mb) * 1024 * 1024
    data = _read_limited(file, max_bytes)
    key = f"products/{secrets.token_hex(16)}{ext}"

    if settings.storage_backend.lower() == "s3":
        if not all((settings.s3_endpoint_url, settings.s3_access_key_id, settings.s3_secret_access_key, settings.s3_bucket)):
            raise HTTPException(status_code=503, detail="S3 storage is not fully configured")
        client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key_id,
            aws_secret_access_key=settings.s3_secret_access_key,
            region_name=settings.s3_region,
        )
        client.put_object(Bucket=settings.s3_bucket, Key=key, Body=data, ContentType=file.content_type)
        base = settings.s3_public_base_url.rstrip("/")
        return f"{base}/{key}" if base else key

    target = settings.upload_path / key
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return f"/media/{key}"
