import factory
from factory.django import DjangoModelFactory

from apps.accounts.tests.factories import UserFactory
from apps.catalog.tests.factories import AudioTrackFactory
from apps.playlists.models import (
    Playlist,
    PlaylistItem,
    PlaylistType,
    PlaylistVisibility,
)


class PlaylistFactory(DjangoModelFactory):
    class Meta:
        model = Playlist

    owner = factory.SubFactory(UserFactory)
    title_ne = factory.Sequence(lambda number: f"प्लेलिस्ट {number}")
    title_en = factory.Sequence(lambda number: f"Playlist {number}")
    playlist_type = PlaylistType.USER
    visibility = PlaylistVisibility.PRIVATE
    is_published = True

    class Params:
        editorial = factory.Trait(
            owner=None,
            playlist_type=PlaylistType.EDITORIAL,
            visibility=PlaylistVisibility.PUBLIC,
        )
        featured = factory.Trait(
            owner=None,
            playlist_type=PlaylistType.EDITORIAL,
            is_featured=True,
        )


class PlaylistItemFactory(DjangoModelFactory):
    class Meta:
        model = PlaylistItem

    playlist = factory.SubFactory(PlaylistFactory)
    track = factory.SubFactory(AudioTrackFactory)
    position = factory.Sequence(lambda number: number + 1)
    added_by = factory.SelfAttribute("playlist.owner")
