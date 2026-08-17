import hashlib
import uuid
from urllib.parse import urlencode

from django.core.cache import cache


class PublicCacheKeys:
    PREFIX = "sunnekatha:public"

    @classmethod
    def version_key(cls, namespace):
        return f"{cls.PREFIX}:version:{namespace}"

    @classmethod
    def version(cls, namespace):
        return cache.get(cls.version_key(namespace), "base")

    @classmethod
    def key(cls, namespace, *, identifier=None, query=None, host=None):
        parts = [cls.PREFIX, namespace, f"v{cls.version(namespace)}"]
        if identifier:
            parts.append(str(identifier))
        if host:
            parts.append(hashlib.sha256(host.encode()).hexdigest()[:12])
        if query:
            normalized = urlencode(sorted(query.lists()), doseq=True)
            parts.append(hashlib.sha256(normalized.encode()).hexdigest()[:16])
        return ":".join(parts)


class PublicCacheInvalidation:
    MODEL_NAMESPACES = {
        "accounts.user": (
            "featured-narrators",
            "playlist-detail",
            "home",
        ),
        "authors.author": (
            "featured-authors",
            "track-detail",
            "playlist-detail",
            "home",
        ),
        "narrators.narrator": (
            "featured-narrators",
            "track-detail",
            "playlist-detail",
            "home",
        ),
        "taxonomy.genre": ("genres", "track-detail", "playlist-detail", "home"),
        "taxonomy.mood": ("moods", "track-detail", "playlist-detail", "home"),
        "taxonomy.language": ("track-detail", "playlist-detail"),
        "taxonomy.contentcategory": (
            "content-categories",
            "track-detail",
            "playlist-detail",
            "home",
        ),
        "playlists.playlist": ("featured-playlists", "playlist-detail", "home"),
        "playlists.playlistitem": (
            "featured-playlists",
            "playlist-detail",
            "home",
        ),
        "catalog.audiotrack": (
            "track-detail",
            "playlist-detail",
            "home",
        ),
        "catalog.literarywork": ("track-detail", "playlist-detail", "home"),
        "catalog.album": ("track-detail", "playlist-detail", "home"),
        "home.homesection": ("home",),
        "home.homesectionitem": ("home",),
    }

    @staticmethod
    def invalidate(*namespaces):
        for namespace in set(namespaces):
            cache.set(
                PublicCacheKeys.version_key(namespace),
                uuid.uuid4().hex,
                timeout=None,
            )

    @classmethod
    def for_model(cls, model_or_instance):
        meta = getattr(model_or_instance, "_meta", None)
        if meta is None:
            meta = model_or_instance.__class__._meta
        cls.invalidate(*cls.MODEL_NAMESPACES.get(meta.label_lower, ()))


public_cache_keys = PublicCacheKeys()
public_cache_invalidation = PublicCacheInvalidation()
