"""Reusable validation at upload and API trust boundaries."""

from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator

IMAGE_EXTENSIONS = ("jpg", "jpeg", "png", "webp", "avif")
AUDIO_EXTENSIONS = ("mp3", "m4a", "aac", "ogg", "wav", "flac")
IMAGE_CONTENT_TYPES = frozenset(
    {
        "image/jpeg",
        "image/jpg",
        "image/pjpeg",
        "image/png",
        "image/webp",
        "image/avif",
    }
)
AUDIO_CONTENT_TYPES = frozenset(
    {
        "audio/mpeg",
        "audio/mp4",
        "audio/aac",
        "audio/ogg",
        "audio/wav",
        "audio/x-wav",
        "audio/flac",
        "audio/x-flac",
    }
)
PERMISSION_DOCUMENT_EXTENSIONS = ("pdf", "jpg", "jpeg", "png")
PERMISSION_DOCUMENT_CONTENT_TYPES = frozenset(
    {"application/pdf", "image/jpeg", "image/png"}
)
CONTENT_TYPE_ALIASES = {
    "image/jpg": "image/jpeg",
    "image/pjpeg": "image/jpeg",
}


def normalize_content_type(value: str | None) -> str:
    content_type = (value or "").split(";", 1)[0].strip().lower()
    return CONTENT_TYPE_ALIASES.get(content_type, content_type)


def validate_image_upload(value) -> None:
    FileExtensionValidator(allowed_extensions=IMAGE_EXTENSIONS)(value)
    _validate_file(
        value,
        max_bytes=getattr(settings, "MAX_IMAGE_UPLOAD_BYTES", 10 * 1024 * 1024),
        allowed_content_types=IMAGE_CONTENT_TYPES,
        label="image",
    )


def validate_audio_upload(value) -> None:
    FileExtensionValidator(allowed_extensions=AUDIO_EXTENSIONS)(value)
    _validate_file(
        value,
        max_bytes=getattr(settings, "MAX_AUDIO_UPLOAD_BYTES", 500 * 1024 * 1024),
        allowed_content_types=AUDIO_CONTENT_TYPES,
        label="audio",
    )


def validate_permission_document_upload(value) -> None:
    FileExtensionValidator(allowed_extensions=PERMISSION_DOCUMENT_EXTENSIONS)(value)
    _validate_file(
        value,
        max_bytes=getattr(
            settings,
            "MAX_PERMISSION_DOCUMENT_BYTES",
            20 * 1024 * 1024,
        ),
        allowed_content_types=PERMISSION_DOCUMENT_CONTENT_TYPES,
        label="permission document",
    )
    position = value.tell() if hasattr(value, "tell") else None
    sample = value.read(16)
    if position is not None:
        value.seek(position)
    extension = Path(value.name).suffix.lower()
    matches = {
        ".pdf": sample.startswith(b"%PDF-"),
        ".jpg": sample.startswith(b"\xff\xd8\xff"),
        ".jpeg": sample.startswith(b"\xff\xd8\xff"),
        ".png": sample.startswith(b"\x89PNG\r\n\x1a\n"),
    }
    if not matches.get(extension, False):
        raise ValidationError(
            "Permission document contents do not match its extension.",
            code="invalid_file_signature",
        )


def validate_slug_segment(value: str) -> None:
    """Reject path separators and traversal in externally supplied path segments."""

    if not value or value in {".", ".."} or Path(value).name != value:
        raise ValidationError("Enter a safe path segment.", code="unsafe_path")


def _validate_file(value, *, max_bytes, allowed_content_types, label) -> None:
    if value.size <= 0:
        raise ValidationError(
            f"The {label} must not be empty.",
            code="empty_file",
        )
    if value.size > max_bytes:
        max_megabytes = max_bytes // (1024 * 1024)
        raise ValidationError(
            f"The {label} must not exceed {max_megabytes} MB.",
            code="file_too_large",
        )

    content_type = normalize_content_type(getattr(value, "content_type", None))
    if not content_type or content_type not in allowed_content_types:
        raise ValidationError(
            f"Unsupported {label} content type.",
            code="invalid_content_type",
        )
