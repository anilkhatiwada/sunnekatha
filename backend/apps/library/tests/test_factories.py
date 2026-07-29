import pytest

from apps.library.tests.factories import (
    FavoriteTrackFactory,
    FollowedAuthorFactory,
    FollowedNarratorFactory,
    ListeningProgressFactory,
    SavedPlaylistFactory,
)

pytestmark = pytest.mark.django_db


def test_library_factories_create_valid_relationships():
    favorite = FavoriteTrackFactory()
    saved = SavedPlaylistFactory()
    followed_author = FollowedAuthorFactory()
    followed_narrator = FollowedNarratorFactory()
    progress = ListeningProgressFactory()

    assert favorite.user_id and favorite.track_id
    assert saved.user_id and saved.playlist_id
    assert followed_author.user_id and followed_author.author_id
    assert followed_narrator.user_id and followed_narrator.narrator_id
    assert progress.position_seconds < progress.duration_seconds
