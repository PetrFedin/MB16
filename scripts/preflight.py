"""Validate MB16 configuration before production startup."""

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.config import get_settings


def main() -> None:
    settings = get_settings()
    errors: list[str] = []

    try:
        ZoneInfo(settings.app_timezone)
    except ZoneInfoNotFoundError:
        errors.append(f"APP_TIMEZONE is invalid: {settings.app_timezone}")

    if settings.max_image_mb <= 0:
        errors.append("MAX_IMAGE_MB must be positive")
    if settings.max_video_mb <= 0:
        errors.append("MAX_VIDEO_MB must be positive")

    if settings.app_env == "production":
        if settings.database_url.startswith("sqlite"):
            errors.append("DATABASE_URL must point to PostgreSQL in production")
        if not settings.telegram_bot_token:
            errors.append("TELEGRAM_BOT_TOKEN is required in production")
        if not settings.admin_ids:
            errors.append("ADMIN_TELEGRAM_IDS must contain at least one numeric Telegram ID")

        if settings.storage_backend.lower() == "s3":
            required = {
                "S3_ENDPOINT_URL": settings.s3_endpoint_url,
                "S3_ACCESS_KEY_ID": settings.s3_access_key_id,
                "S3_SECRET_ACCESS_KEY": settings.s3_secret_access_key,
                "S3_BUCKET": settings.s3_bucket,
                "S3_PUBLIC_BASE_URL": settings.s3_public_base_url,
            }
            for name, value in required.items():
                if not value:
                    errors.append(f"{name} is required when STORAGE_BACKEND=s3")

    if errors:
        print("MB16 preflight failed:")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)

    print("MB16 preflight OK")


if __name__ == "__main__":
    main()
