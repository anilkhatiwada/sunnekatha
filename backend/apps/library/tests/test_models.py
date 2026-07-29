import pytest
from django.db import IntegrityError

from apps.accounts.tests.factories import UserFactory
from apps.authors.tests.factories import AuthorFactory
from apps.catalog.tests.factories import AudioTrackFactory
from apps.library.models import FavoriteTrack, FollowedAuthor

pytestmark = pytest.mark.django_db


def test_favorite_track_database_constraint_prevents_duplicates():
    user = UserFactory()
    track = AudioTrackFactory()
    FavoriteTrack.objects.create(user=user, track=track)

    with pytest.raises(IntegrityError):
        FavoriteTrack.objects.create(user=user, track=track)


def test_followed_author_database_constraint_prevents_duplicates():
    user = UserFactory()
    author = AuthorFactory()
    FollowedAuthor.objects.create(user=user, author=author)

    with pytest.raises(IntegrityError):
        FollowedAuthor.objects.create(user=user, author=author)
