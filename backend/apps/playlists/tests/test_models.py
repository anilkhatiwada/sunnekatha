import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from apps.accounts.tests.factories import UserFactory
from apps.playlists.models import PlaylistType
from apps.playlists.tests.factories import PlaylistFactory, PlaylistItemFactory

pytestmark = pytest.mark.django_db


def test_user_playlist_requires_owner():
    playlist = PlaylistFactory.build(owner=None)

    with pytest.raises(ValidationError):
        playlist.full_clean(exclude={"slug"})


def test_editorial_playlist_cannot_have_owner():
    playlist = PlaylistFactory.build(
        owner=UserFactory(),
        playlist_type=PlaylistType.EDITORIAL,
    )

    with pytest.raises(ValidationError):
        playlist.full_clean(exclude={"slug"})


def test_playlist_rejects_duplicate_track_and_position():
    item = PlaylistItemFactory()

    with pytest.raises(IntegrityError):
        PlaylistItemFactory(
            playlist=item.playlist,
            track=item.track,
            position=item.position + 1,
        )
