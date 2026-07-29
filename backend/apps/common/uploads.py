"""Collision-resistant upload paths that do not trust original filenames."""

import uuid
from pathlib import Path


def image_upload_path(instance, filename: str) -> str:
    return cover_upload_path(instance, filename)


def audio_upload_path(instance, filename: str) -> str:
    return original_audio_upload_path(instance, filename)


def cover_upload_path(instance, filename: str) -> str:
    return _upload_path(instance, filename, prefix="covers")


def original_audio_upload_path(instance, filename: str) -> str:
    return _upload_path(instance, filename, prefix="originals/audio")


def processed_audio_upload_path(instance, filename: str) -> str:
    return _upload_path(instance, filename, prefix="processed/audio")


def temporary_upload_path(instance, filename: str) -> str:
    return _upload_path(instance, filename, prefix="temporary/uploads")


def permission_document_upload_path(instance, filename: str) -> str:
    return _upload_path(instance, filename, prefix="originals/permission-documents")


def _upload_path(instance, filename: str, *, prefix: str) -> str:
    model_name = instance._meta.model_name
    instance_id = getattr(instance, "pk", None) or "unassigned"
    extension = Path(filename).suffix.lower()
    safe_extension = (
        extension if extension.isascii() and extension[1:].isalnum() else ""
    )
    generated_name = f"{uuid.uuid4().hex}{safe_extension}"
    return f"{prefix}/{model_name}/{instance_id}/{generated_name}"
