import uuid
from datetime import timedelta
from pathlib import Path, PurePosixPath

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import APIException, ValidationError

from apps.common.validators import (
    AUDIO_CONTENT_TYPES,
    AUDIO_EXTENSIONS,
    IMAGE_CONTENT_TYPES,
    IMAGE_EXTENSIONS,
    normalize_content_type,
)
from apps.uploads.models import UploadSession, UploadStatus, UploadType


class UploadStorageUnavailable(APIException):
    status_code = 503
    default_detail = "Upload storage is temporarily unavailable."
    default_code = "upload_storage_unavailable"


UPLOAD_RULES = {
    UploadType.AUDIO_MASTER: {
        "extensions": AUDIO_EXTENSIONS,
        "content_types": AUDIO_CONTENT_TYPES,
        "max_setting": "MAX_AUDIO_UPLOAD_BYTES",
        "bucket_setting": "AWS_S3_AUDIO_BUCKET_NAME",
        "prefix": "audio-master",
    },
    UploadType.COVER_IMAGE: {
        "extensions": IMAGE_EXTENSIONS,
        "content_types": IMAGE_CONTENT_TYPES,
        "max_setting": "MAX_IMAGE_UPLOAD_BYTES",
        "bucket_setting": "AWS_S3_COVER_BUCKET_NAME",
        "prefix": "covers",
    },
    UploadType.NARRATOR_IMAGE: {
        "extensions": IMAGE_EXTENSIONS,
        "content_types": IMAGE_CONTENT_TYPES,
        "max_setting": "MAX_IMAGE_UPLOAD_BYTES",
        "bucket_setting": "AWS_S3_COVER_BUCKET_NAME",
        "prefix": "narrators",
    },
    UploadType.AUTHOR_IMAGE: {
        "extensions": IMAGE_EXTENSIONS,
        "content_types": IMAGE_CONTENT_TYPES,
        "max_setting": "MAX_IMAGE_UPLOAD_BYTES",
        "bucket_setting": "AWS_S3_COVER_BUCKET_NAME",
        "prefix": "authors",
    },
}

EXTENSION_CONTENT_TYPES = {
    ".jpg": {"image/jpeg"},
    ".jpeg": {"image/jpeg"},
    ".png": {"image/png"},
    ".webp": {"image/webp"},
    ".avif": {"image/avif"},
    ".mp3": {"audio/mpeg"},
    ".m4a": {"audio/mp4"},
    ".aac": {"audio/aac"},
    ".ogg": {"audio/ogg"},
    ".wav": {"audio/wav", "audio/x-wav"},
    ".flac": {"audio/flac", "audio/x-flac"},
}

# S3 evaluates content-length-range against the complete multipart POST body,
# not only the uploaded object. Allow bounded form overhead and verify the
# object's exact ContentLength during confirmation.
PRESIGNED_POST_OVERHEAD_BYTES = 1024 * 1024


def get_s3_client():
    return boto3.client(
        "s3",
        region_name=settings.AWS_S3_REGION_NAME,
        endpoint_url=settings.AWS_S3_ENDPOINT_URL,
        config=Config(signature_version="s3v4"),
    )


class UploadSessionService:
    def request(self, *, user, upload_type, original_filename, content_type, size):
        self._authorize_request(user)
        self._require_s3()
        content_type = normalize_content_type(content_type)
        rule, extension = self._validate(
            upload_type=upload_type,
            original_filename=original_filename,
            content_type=content_type,
            size=size,
        )
        session = UploadSession(
            user=user,
            upload_type=upload_type,
            original_filename=PurePosixPath(original_filename.replace("\\", "/")).name,
            content_type=content_type.lower(),
            expected_size=size,
            expires_at=timezone.now()
            + timedelta(seconds=settings.UPLOAD_SESSION_EXPIRY_SECONDS),
        )
        session.object_key = (
            f"temporary/uploads/{rule['prefix']}/{user.id}/{session.id}/"
            f"{uuid.uuid4().hex}{extension}"
        )
        session.save()
        bucket = getattr(settings, rule["bucket_setting"])
        try:
            upload = get_s3_client().generate_presigned_post(
                Bucket=bucket,
                Key=session.object_key,
                Fields={
                    "Content-Type": session.content_type,
                    "x-amz-server-side-encryption": "AES256",
                },
                Conditions=[
                    {"key": session.object_key},
                    {"Content-Type": session.content_type},
                    {"x-amz-server-side-encryption": "AES256"},
                    [
                        "content-length-range",
                        size,
                        size + PRESIGNED_POST_OVERHEAD_BYTES,
                    ],
                ],
                ExpiresIn=settings.UPLOAD_SESSION_EXPIRY_SECONDS,
            )
        except (BotoCoreError, ClientError):
            session.delete()
            raise UploadStorageUnavailable from None
        return session, upload

    def confirm(self, *, session, actor):
        self._authorize_session(
            actor, session, permission="uploads.change_uploadsession"
        )
        self._require_s3()
        expired = False
        with transaction.atomic():
            locked = UploadSession.objects.select_for_update().get(pk=session.pk)
            self._expire_if_needed(locked)
            if locked.status == UploadStatus.EXPIRED:
                expired = True
            elif locked.status == UploadStatus.CONFIRMED:
                return locked
            elif locked.status != UploadStatus.PENDING:
                raise ValidationError(
                    {"status": "This upload can no longer be confirmed."}
                )
            else:
                metadata = self._head_object(locked)
                actual_type = metadata.get("ContentType", "").split(";", 1)[0].lower()
                if metadata.get("ContentLength") != locked.expected_size:
                    raise ValidationError(
                        {"expectedSize": "Uploaded object size does not match."}
                    )
                if actual_type != locked.content_type:
                    raise ValidationError(
                        {"contentType": "Uploaded object type does not match."}
                    )
                if metadata.get("ServerSideEncryption") != "AES256":
                    raise ValidationError(
                        {"upload": "Uploaded object encryption is invalid."}
                    )
                self._verify_file_signature(locked)
                locked.status = UploadStatus.CONFIRMED
                locked.actual_size = metadata["ContentLength"]
                locked.save(update_fields=("status", "actual_size", "updated_at"))
                return locked
        if expired:
            raise ValidationError({"status": "This upload session has expired."})
        raise RuntimeError("Unexpected upload confirmation state.")

    @transaction.atomic
    def cancel(self, *, session, actor):
        self._authorize_session(
            actor, session, permission="uploads.change_uploadsession"
        )
        self._require_s3()
        locked = UploadSession.objects.select_for_update().get(pk=session.pk)
        self._expire_if_needed(locked)
        if locked.status == UploadStatus.CANCELED:
            return locked
        if locked.status == UploadStatus.CONFIRMED:
            raise ValidationError({"status": "A confirmed upload cannot be canceled."})
        if locked.status == UploadStatus.PENDING:
            try:
                get_s3_client().delete_object(
                    Bucket=self._bucket(locked),
                    Key=locked.object_key,
                )
            except (BotoCoreError, ClientError):
                raise UploadStorageUnavailable from None
            locked.status = UploadStatus.CANCELED
            locked.temporary_object_deleted_at = timezone.now()
            locked.save(
                update_fields=(
                    "status",
                    "temporary_object_deleted_at",
                    "updated_at",
                )
            )
        return locked

    @transaction.atomic
    def mark_abandoned(self, *, session, actor):
        """Mark an unfinished upload abandoned without touching storage."""
        self._authorize_session(
            actor, session, permission="uploads.change_uploadsession"
        )
        locked = UploadSession.objects.select_for_update().get(pk=session.pk)
        self._expire_if_needed(locked)
        if locked.status == UploadStatus.ABANDONED:
            return locked
        if locked.status not in {
            UploadStatus.PENDING,
            UploadStatus.EXPIRED,
            UploadStatus.CANCELED,
        }:
            raise ValidationError(
                {"status": "Only unfinished uploads can be marked abandoned."}
            )
        locked.status = UploadStatus.ABANDONED
        locked.save(update_fields=("status", "updated_at"))
        return locked

    @transaction.atomic
    def delete_temporary_object(self, *, session, actor):
        """Delete an abandoned temporary object through the configured backend."""
        self._authorize_session(
            actor, session, permission="uploads.delete_uploadsession"
        )
        self._require_s3()
        locked = UploadSession.objects.select_for_update().get(pk=session.pk)
        if locked.temporary_object_deleted_at is not None:
            return locked
        if locked.status not in {
            UploadStatus.CANCELED,
            UploadStatus.EXPIRED,
            UploadStatus.ABANDONED,
        }:
            raise ValidationError(
                {
                    "status": (
                        "Cancel, expire, or abandon the upload before deleting "
                        "its temporary object."
                    )
                }
            )
        try:
            get_s3_client().delete_object(
                Bucket=self._bucket(locked),
                Key=locked.object_key,
            )
        except (BotoCoreError, ClientError):
            raise UploadStorageUnavailable from None
        locked.temporary_object_deleted_at = timezone.now()
        locked.save(update_fields=("temporary_object_deleted_at", "updated_at"))
        return locked

    def refresh_status(self, session, *, actor):
        self._authorize_session(actor, session, permission="uploads.view_uploadsession")
        self._expire_if_needed(session)
        return session

    @staticmethod
    def _authorize_request(user):
        if not (
            user
            and user.is_authenticated
            and user.is_active
            and (user.is_creator or user.is_staff)
        ):
            raise PermissionDenied("Creator or staff upload access is required.")

    @staticmethod
    def _authorize_session(actor, session, *, permission):
        is_owner = bool(
            actor
            and actor.is_authenticated
            and actor.is_active
            and actor.pk == session.user_id
            and (actor.is_creator or actor.is_staff)
        )
        is_authorized_staff = bool(
            actor
            and actor.is_authenticated
            and actor.is_active
            and actor.is_staff
            and actor.has_perm(permission)
        )
        if not (is_owner or is_authorized_staff):
            raise PermissionDenied("You cannot manage this upload session.")

    @staticmethod
    def _expire_if_needed(session):
        if (
            session.status == UploadStatus.PENDING
            and session.expires_at <= timezone.now()
        ):
            session.status = UploadStatus.EXPIRED
            session.save(update_fields=("status", "updated_at"))

    @staticmethod
    def _require_s3():
        if not settings.USE_S3_STORAGE:
            raise UploadStorageUnavailable("Direct uploads require S3 storage.")

    @staticmethod
    def _bucket(session):
        rule = UPLOAD_RULES[session.upload_type]
        return getattr(settings, rule["bucket_setting"])

    def _head_object(self, session):
        try:
            return get_s3_client().head_object(
                Bucket=self._bucket(session),
                Key=session.object_key,
            )
        except ClientError as exc:
            code = str(exc.response.get("Error", {}).get("Code", ""))
            if code in {"404", "NoSuchKey", "NotFound"}:
                raise ValidationError(
                    {"upload": "The uploaded object does not exist."}
                ) from None
            raise UploadStorageUnavailable from None
        except BotoCoreError:
            raise UploadStorageUnavailable from None

    def _verify_file_signature(self, session):
        try:
            response = get_s3_client().get_object(
                Bucket=self._bucket(session),
                Key=session.object_key,
                Range="bytes=0-4095",
            )
            sample = response["Body"].read(4096)
        except (BotoCoreError, ClientError, KeyError, AttributeError):
            raise UploadStorageUnavailable from None
        extension = Path(session.original_filename).suffix.lower()
        if not self._matches_signature(extension, sample):
            raise ValidationError(
                {"upload": "Uploaded file contents do not match its declared type."}
            )

    @staticmethod
    def _matches_signature(extension, sample):
        if extension in {".jpg", ".jpeg"}:
            return sample.startswith(b"\xff\xd8\xff")
        if extension == ".png":
            return sample.startswith(b"\x89PNG\r\n\x1a\n")
        if extension == ".webp":
            return sample.startswith(b"RIFF") and sample[8:12] == b"WEBP"
        if extension == ".avif":
            return sample[4:12] in {b"ftypavif", b"ftypavis"}
        if extension == ".mp3":
            return sample.startswith(b"ID3") or (
                len(sample) >= 2 and sample[0] == 0xFF and sample[1] & 0xE0 == 0xE0
            )
        if extension == ".m4a":
            return sample[4:8] == b"ftyp"
        if extension == ".aac":
            return (
                len(sample) >= 2
                and sample[0] == 0xFF
                and sample[1] & 0xF6 in {0xF0, 0xF2}
            )
        if extension == ".ogg":
            return sample.startswith(b"OggS")
        if extension == ".wav":
            return sample.startswith(b"RIFF") and sample[8:12] == b"WAVE"
        if extension == ".flac":
            return sample.startswith(b"fLaC")
        return False

    @staticmethod
    def _validate(*, upload_type, original_filename, content_type, size):
        rule = UPLOAD_RULES[upload_type]
        if any(ord(character) < 32 for character in original_filename):
            raise ValidationError(
                {"originalFilename": "Filename contains invalid characters."}
            )
        extension = Path(original_filename).suffix.lower()
        if extension.removeprefix(".") not in rule["extensions"]:
            raise ValidationError({"originalFilename": "Unsupported file extension."})
        normalized_type = normalize_content_type(content_type)
        if normalized_type not in rule["content_types"]:
            raise ValidationError({"contentType": "Unsupported content type."})
        if normalized_type not in EXTENSION_CONTENT_TYPES.get(extension, set()):
            raise ValidationError(
                {"contentType": ("Content type does not match the filename extension.")}
            )
        maximum = getattr(settings, rule["max_setting"])
        if size <= 0 or size > maximum:
            raise ValidationError(
                {"expectedSize": f"File size must be between 1 and {maximum} bytes."}
            )
        return rule, extension


upload_session_service = UploadSessionService()
