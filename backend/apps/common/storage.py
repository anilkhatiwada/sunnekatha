from pathlib import Path

from django.conf import settings
from django.core.files.storage import FileSystemStorage, storages
from storages.backends.s3 import S3Storage


class SecureS3Storage(S3Storage):
    default_acl = "private"
    file_overwrite = False
    querystring_auth = True
    object_parameters = {
        "CacheControl": "private, max-age=0, no-store",
        "ServerSideEncryption": "AES256",
    }


class PrivateOriginalAudioStorage(SecureS3Storage):
    location = ""


class PrivateProcessedAudioStorage(SecureS3Storage):
    location = ""

    object_parameters = {
        "CacheControl": "private, max-age=3600",
        "ServerSideEncryption": "AES256",
    }


class CoverImageStorage(SecureS3Storage):
    location = ""
    object_parameters = {
        "CacheControl": "public, max-age=86400",
        "ServerSideEncryption": "AES256",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.custom_domain:
            self.querystring_auth = False
            self.url_protocol = "https:"


class TemporaryUploadStorage(SecureS3Storage):
    location = ""


class LocalLifecycleStorage(FileSystemStorage):
    path_prefix = ""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("location", Path(settings.MEDIA_ROOT) / self.path_prefix)
        base_url = settings.MEDIA_URL
        if self.path_prefix:
            base_url = f"{base_url.rstrip('/')}/{self.path_prefix}/"
        kwargs.setdefault("base_url", base_url)
        super().__init__(*args, **kwargs)


class LocalOriginalAudioStorage(LocalLifecycleStorage):
    pass


class LocalProcessedAudioStorage(LocalLifecycleStorage):
    pass


class LocalCoverImageStorage(LocalLifecycleStorage):
    pass


class LocalTemporaryUploadStorage(LocalLifecycleStorage):
    pass


def original_audio_storage():
    return storages["original_audio"]


def processed_audio_storage():
    return storages["processed_audio"]


def temporary_upload_storage():
    return storages["temporary_uploads"]
