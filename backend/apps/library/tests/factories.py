from decimal import Decimal

import factory
from django.utils import timezone
from factory.django import DjangoModelFactory

from apps.accounts.tests.factories import UserFactory
from apps.authors.tests.factories import AuthorFactory
from apps.catalog.tests.factories import AudioTrackFactory
from apps.library.models import (
    FavoriteTrack,
    FollowedAuthor,
    FollowedNarrator,
    ListeningProgress,
    SavedPlaylist,
)
from apps.narrators.tests.factories import NarratorFactory
from apps.playlists.tests.factories import PlaylistFactory


class FavoriteTrackFactory(DjangoModelFactory):
    class Meta:
        model = FavoriteTrack

    user = factory.SubFactory(UserFactory)
    track = factory.SubFactory(AudioTrackFactory)


class SavedPlaylistFactory(DjangoModelFactory):
    class Meta:
        model = SavedPlaylist

    user = factory.SubFactory(UserFactory)
    playlist = factory.SubFactory(PlaylistFactory)


class FollowedAuthorFactory(DjangoModelFactory):
    class Meta:
        model = FollowedAuthor

    user = factory.SubFactory(UserFactory)
    author = factory.SubFactory(AuthorFactory)


class FollowedNarratorFactory(DjangoModelFactory):
    class Meta:
        model = FollowedNarrator

    user = factory.SubFactory(UserFactory)
    narrator = factory.SubFactory(NarratorFactory)


class ListeningProgressFactory(DjangoModelFactory):
    class Meta:
        model = ListeningProgress

    user = factory.SubFactory(UserFactory)
    track = factory.SubFactory(AudioTrackFactory)
    position_seconds = Decimal("120")
    duration_seconds = factory.LazyAttribute(
        lambda progress: Decimal(progress.track.duration_seconds)
    )
    progress_percentage = factory.LazyAttribute(
        lambda progress: (
            progress.position_seconds / progress.duration_seconds * Decimal("100")
        ).quantize(Decimal("0.01"))
    )
    is_completed = False
    last_listened_at = factory.LazyFunction(timezone.now)
