from dataclasses import dataclass
from datetime import timedelta
from functools import lru_cache
from pathlib import PurePosixPath
from urllib.parse import quote

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from botocore.signers import CloudFrontSigner
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from django.conf import settings
from django.utils import timezone
from rest_framework.exceptions import APIException, PermissionDenied, ValidationError

from apps.subscriptions.permissions import premium_access_type


class MediaDeliveryUnavailable(APIException):
    status_code = 503
    default_detail = "Media delivery is temporarily unavailable."
    default_code = "media_delivery_unavailable"


@dataclass(frozen=True)
class MediaAuthorization:
    access_type: str
    is_entitled: bool
    is_privileged: bool


@lru_cache(maxsize=4)
def load_private_key(private_key_text):
    normalized = private_key_text.replace("\\n", "\n").encode()
    return serialization.load_pem_private_key(normalized, password=None)


class CloudFrontMediaService:
    qualities = ("low", "high", "auto")

    def deliver(self, track, *, quality, request):
        if quality not in self.qualities:
            raise ValidationError({"quality": "Select low, high, or auto."})
        is_public = track.is_published and track.published_at <= timezone.now()
        authorization = self.authorize(
            track,
            user=getattr(request, "user", None),
            is_public=is_public,
        )
        selected_quality, file_field = self._select_file(track, quality)
        if not self._cloudfront_enabled():
            expires_at = self._signed_expiration()
            return {
                "quality": selected_quality,
                "url": self._s3_signed_url(file_field.name),
                "expiresAt": expires_at,
                "authorization": {
                    "status": "authorized",
                    "accessType": authorization.access_type,
                    "isEntitled": authorization.is_entitled,
                    "isPrivileged": authorization.is_privileged,
                },
            }
        access_class = (
            "premium" if track.is_premium else "restricted" if not is_public else "free"
        )
        resource_url = self._resource_url(file_field.name, access_class)
        requires_signature = track.is_premium or not is_public
        expires_at = None
        url = resource_url
        if requires_signature:
            expires_at = self._signed_expiration()
            url = self._signed_url(resource_url, expires_at)
        return {
            "quality": selected_quality,
            "url": url,
            "expiresAt": expires_at,
            "authorization": {
                "status": "authorized",
                "accessType": authorization.access_type,
                "isEntitled": authorization.is_entitled,
                "isPrivileged": authorization.is_privileged,
            },
        }

    def deliver_admin_object(self, *, object_key, quality, user):
        """Return signed CloudFront access for a server-controlled private key."""
        is_staff = bool(
            user and user.is_authenticated and user.is_active and user.is_staff
        )
        if not is_staff:
            raise PermissionDenied("Authorized staff access is required.")
        if quality != "original":
            raise ValidationError({"quality": "Only original upload preview is valid."})
        normalized_key = PurePosixPath(object_key)
        if (
            normalized_key.is_absolute()
            or ".." in normalized_key.parts
            or normalized_key.parts[:3] != ("temporary", "uploads", "audio-master")
        ):
            raise ValidationError({"objectKey": "Audio preview object key is invalid."})
        resource_url = self._resource_url(object_key, "restricted")
        expires_at = self._signed_expiration()
        return {
            "quality": quality,
            "url": self._signed_url(resource_url, expires_at),
            "expiresAt": expires_at,
        }

    def deliver_admin_document(self, *, object_key, user):
        """Return short-lived CloudFront access to a private rights document."""
        is_authorized = bool(
            user
            and user.is_authenticated
            and user.is_active
            and user.is_staff
            and (
                user.has_perm("catalog.view_permissiondocument")
                or user.has_perm("catalog.change_permissiondocument")
            )
        )
        if not is_authorized:
            raise PermissionDenied("Authorized rights staff access is required.")
        normalized_key = PurePosixPath(object_key)
        if (
            normalized_key.is_absolute()
            or ".." in normalized_key.parts
            or normalized_key.parts[:2] != ("originals", "permission-documents")
        ):
            raise ValidationError({"objectKey": "Permission document key is invalid."})
        resource_url = self._resource_url(object_key, "restricted")
        expires_at = self._signed_expiration()
        return {
            "url": self._signed_url(resource_url, expires_at),
            "expiresAt": expires_at,
        }

    def authorize(self, track, *, user, is_public):
        is_staff = bool(
            user and user.is_authenticated and user.is_active and user.is_staff
        )
        is_creator = bool(
            user
            and user.is_authenticated
            and user.is_active
            and user.is_creator
            and track.narrator.user_id == user.id
        )
        if not is_public and not (is_staff or is_creator):
            from rest_framework.exceptions import NotFound

            raise NotFound("Track not found.")
        if is_staff:
            return MediaAuthorization("staff", False, True)
        if is_creator:
            return MediaAuthorization("creator", False, True)
        if not track.is_premium:
            return MediaAuthorization("free", False, False)
        if not user or not user.is_authenticated or not user.is_active:
            raise PermissionDenied("An active premium entitlement is required.")
        access_type = premium_access_type(user, track=track)
        if not access_type:
            raise PermissionDenied("An active premium entitlement is required.")
        return MediaAuthorization(access_type, True, False)

    @staticmethod
    def _select_file(track, requested_quality):
        if requested_quality == "auto":
            if track.stream_file_high:
                return "high", track.stream_file_high
            if track.stream_file_low:
                return "low", track.stream_file_low
        else:
            file_field = getattr(track, f"stream_file_{requested_quality}")
            if file_field:
                return requested_quality, file_field
        raise ValidationError({"quality": "The requested quality is unavailable."})

    @staticmethod
    def _resource_url(object_name, access_class):
        domain = settings.CLOUDFRONT_MEDIA_DOMAIN.strip().removeprefix("https://")
        domain = domain.removeprefix("http://").rstrip("/")
        if not domain:
            raise MediaDeliveryUnavailable(
                "CloudFront media delivery is not configured."
            )
        object_path = quote(object_name.lstrip("/"), safe="/")
        return f"https://{domain}/{access_class}/{object_path}"

    @staticmethod
    def _cloudfront_enabled():
        configured = bool(settings.CLOUDFRONT_MEDIA_DOMAIN.strip())
        return getattr(settings, "CLOUDFRONT_MEDIA_ENABLED", configured)

    @staticmethod
    def _s3_signed_url(object_name):
        if not settings.USE_S3_STORAGE or not settings.AWS_S3_AUDIO_BUCKET_NAME:
            raise MediaDeliveryUnavailable("Private S3 media delivery is unavailable.")
        try:
            client = boto3.client(
                "s3",
                region_name=settings.AWS_S3_REGION_NAME,
                endpoint_url=settings.AWS_S3_ENDPOINT_URL,
                config=Config(signature_version="s3v4"),
            )
            return client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": settings.AWS_S3_AUDIO_BUCKET_NAME,
                    "Key": object_name,
                },
                ExpiresIn=settings.CLOUDFRONT_SIGNED_URL_EXPIRE_SECONDS,
            )
        except (BotoCoreError, ClientError):
            raise MediaDeliveryUnavailable(
                "Private S3 media delivery is temporarily unavailable."
            ) from None

    @staticmethod
    def _signed_expiration():
        lifetime = settings.CLOUDFRONT_SIGNED_URL_EXPIRE_SECONDS
        if not 30 <= lifetime <= 900:
            raise MediaDeliveryUnavailable(
                "CloudFront signed URL lifetime is not securely configured."
            )
        return timezone.now() + timedelta(seconds=lifetime)

    @staticmethod
    def _signed_url(resource_url, expires_at):
        if not settings.CLOUDFRONT_KEY_PAIR_ID or not settings.CLOUDFRONT_PRIVATE_KEY:
            raise MediaDeliveryUnavailable(
                "CloudFront signed media delivery is not configured."
            )
        try:
            private_key = load_private_key(settings.CLOUDFRONT_PRIVATE_KEY)
        except (TypeError, ValueError):
            raise MediaDeliveryUnavailable(
                "CloudFront signing configuration is invalid."
            ) from None

        def rsa_signer(message):
            return private_key.sign(message, padding.PKCS1v15(), hashes.SHA1())

        signer = CloudFrontSigner(settings.CLOUDFRONT_KEY_PAIR_ID, rsa_signer)
        return signer.generate_presigned_url(
            resource_url,
            date_less_than=expires_at,
        )


cloudfront_media_service = CloudFrontMediaService()


class TrackMediaURLService:
    """Backward-compatible player output, backed only by CloudFront."""

    def get_access_urls(self, track, *, request=None):
        urls = {}
        for quality in ("high", "low"):
            try:
                delivery = cloudfront_media_service.deliver(
                    track,
                    quality=quality,
                    request=request,
                )
                urls[quality] = delivery["url"]
            except (PermissionDenied, ValidationError, MediaDeliveryUnavailable):
                urls[quality] = None
        return urls


track_media_url_service = TrackMediaURLService()
