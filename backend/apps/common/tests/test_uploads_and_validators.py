from types import SimpleNamespace
from uuid import uuid4

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models.fields.files import ImageFieldFile

from apps.authors.models import Author
from apps.common.storage import (
    CoverImageStorage,
    LocalCoverImageStorage,
    LocalOriginalAudioStorage,
    LocalProcessedAudioStorage,
    LocalTemporaryUploadStorage,
    PrivateOriginalAudioStorage,
    PrivateProcessedAudioStorage,
    TemporaryUploadStorage,
)
from apps.common.uploads import (
    image_upload_path,
    original_audio_upload_path,
    processed_audio_upload_path,
    temporary_upload_path,
)
from apps.common.validators import (
    validate_audio_upload,
    validate_image_upload,
    validate_permission_document_upload,
    validate_slug_segment,
)


def test_upload_paths_are_scoped_and_discard_untrusted_filename():
    instance_id = uuid4()
    instance = SimpleNamespace(
        pk=instance_id,
        _meta=SimpleNamespace(model_name="track"),
    )

    image_path = image_upload_path(instance, "../../Portrait.WEBP")
    original_path = original_audio_upload_path(instance, "../recording.MP3")
    processed_path = processed_audio_upload_path(instance, "../stream.M4A")
    temporary_path = temporary_upload_path(instance, "../../draft.WAV")

    assert image_path.startswith(f"covers/track/{instance_id}/")
    assert image_path.endswith(".webp")
    assert "Portrait" not in image_path
    assert original_path.startswith(f"originals/audio/track/{instance_id}/")
    assert original_path.endswith(".mp3")
    assert "recording" not in original_path
    assert processed_path.startswith(f"processed/audio/track/{instance_id}/")
    assert processed_path.endswith(".m4a")
    assert temporary_path.startswith(f"temporary/uploads/track/{instance_id}/")
    assert temporary_path.endswith(".wav")
    assert ".." not in temporary_path


def test_s3_storage_classes_are_private_and_rooted_for_legacy_keys():
    storage_classes = (
        PrivateOriginalAudioStorage,
        PrivateProcessedAudioStorage,
        CoverImageStorage,
        TemporaryUploadStorage,
    )

    for storage_class in storage_classes:
        storage = storage_class(bucket_name="sunnekatha-test")
        assert storage.default_acl == "private"
        assert storage.file_overwrite is False
        assert storage.location == ""
        assert storage.object_parameters["ServerSideEncryption"] == "AES256"

    assert PrivateOriginalAudioStorage(bucket_name="sunnekatha-test").querystring_auth
    assert PrivateProcessedAudioStorage(bucket_name="sunnekatha-test").querystring_auth
    assert TemporaryUploadStorage(bucket_name="sunnekatha-test").querystring_auth


def test_cover_storage_uses_https_cloudfront_without_public_acl():
    storage = CoverImageStorage(
        bucket_name="sunnekatha-covers",
        custom_domain="media.example.com",
    )

    assert storage.default_acl == "private"
    assert storage.querystring_auth is False
    assert storage.url_protocol == "https:"


def test_local_storage_fallbacks_share_root_for_legacy_keys(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    settings.MEDIA_URL = "/media/"

    local_storages = (
        LocalOriginalAudioStorage(),
        LocalProcessedAudioStorage(),
        LocalCoverImageStorage(),
        LocalTemporaryUploadStorage(),
    )

    for storage in local_storages:
        assert storage.location == str(tmp_path)
        assert storage.base_url == "/media/"


def test_image_validator_accepts_supported_upload():
    upload = SimpleUploadedFile(
        "cover.webp",
        b"image-data",
        content_type="image/webp",
    )

    validate_image_upload(upload)


@pytest.mark.parametrize(
    "content_type",
    ["image/jpeg", "image/jpg", "image/pjpeg", "image/jpeg; charset=binary"],
)
def test_image_validator_accepts_jpeg_content_type_aliases(content_type):
    upload = SimpleUploadedFile(
        "cover.jpg",
        b"image-data",
        content_type=content_type,
    )

    validate_image_upload(upload)


def test_image_validator_reads_content_type_from_model_field_wrapper():
    upload = SimpleUploadedFile(
        "cover.jpg",
        b"image-data",
        content_type="image/jpeg",
    )
    author = Author(name_ne="लेखक", name_en="Author")
    field = author._meta.get_field("image")
    wrapped = ImageFieldFile(author, field, upload.name)
    wrapped.file = upload

    validate_image_upload(wrapped)


def test_audio_validator_rejects_mismatched_content_type():
    upload = SimpleUploadedFile(
        "story.mp3",
        b"audio-data",
        content_type="application/pdf",
    )

    with pytest.raises(ValidationError, match="Unsupported audio content type"):
        validate_audio_upload(upload)


def test_upload_validator_rejects_missing_content_type():
    upload = SimpleUploadedFile("story.mp3", b"audio-data")

    with pytest.raises(ValidationError, match="Unsupported audio content type"):
        validate_audio_upload(upload)


def test_image_validator_enforces_configured_size(settings):
    settings.MAX_IMAGE_UPLOAD_BYTES = 2
    upload = SimpleUploadedFile(
        "cover.png",
        b"too-large",
        content_type="image/png",
    )

    with pytest.raises(ValidationError) as exc_info:
        validate_image_upload(upload)

    assert exc_info.value.code == "file_too_large"


def test_permission_document_validator_checks_file_signature(settings):
    settings.MAX_PERMISSION_DOCUMENT_BYTES = 1024
    valid = SimpleUploadedFile(
        "permission.pdf",
        b"%PDF-1.7 secure permission",
        content_type="application/pdf",
    )
    disguised = SimpleUploadedFile(
        "permission.pdf",
        b"not a pdf",
        content_type="application/pdf",
    )

    validate_permission_document_upload(valid)
    with pytest.raises(ValidationError, match="contents"):
        validate_permission_document_upload(disguised)


@pytest.mark.parametrize("value", ["../secret", "nested/path", ".", ""])
def test_slug_segment_rejects_unsafe_paths(value):
    with pytest.raises(ValidationError):
        validate_slug_segment(value)
