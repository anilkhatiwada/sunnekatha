from django.db.models.signals import m2m_changed, post_delete, post_save
from django.dispatch import receiver

from apps.accounts.models import User
from apps.authors.models import Author
from apps.catalog.models import Album, AudioTrack, LiteraryWork
from apps.common.cache import public_cache_invalidation
from apps.home.models import HomeSection, HomeSectionItem
from apps.narrators.models import Narrator
from apps.playlists.models import Playlist
from apps.taxonomy.models import Genre, Language, Mood


@receiver([post_save, post_delete], sender=HomeSection)
@receiver([post_save, post_delete], sender=HomeSectionItem)
@receiver([post_save, post_delete], sender=AudioTrack)
@receiver([post_save, post_delete], sender=Playlist)
@receiver([post_save, post_delete], sender=Album)
@receiver([post_save, post_delete], sender=Author)
@receiver([post_save, post_delete], sender=Narrator)
@receiver([post_save, post_delete], sender=Genre)
@receiver([post_save, post_delete], sender=Mood)
@receiver([post_save, post_delete], sender=Language)
@receiver([post_save, post_delete], sender=LiteraryWork)
@receiver([post_save, post_delete], sender=User)
def clear_homepage_cache(**kwargs):
    public_cache_invalidation.for_model(kwargs["sender"])


@receiver(m2m_changed, sender=LiteraryWork.genres.through)
@receiver(m2m_changed, sender=LiteraryWork.moods.through)
def clear_track_metadata_cache(**kwargs):
    if kwargs["action"].startswith("post_"):
        public_cache_invalidation.invalidate(
            "track-detail",
            "playlist-detail",
            "home",
        )
