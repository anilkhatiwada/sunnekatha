import pytest
from django.db import IntegrityError

from apps.accounts.tests.factories import UserFactory
from apps.catalog.tests.factories import AudioTrackFactory
from apps.library.models import ListeningProgress

pytestmark = pytest.mark.django_db


def test_one_progress_record_per_user_and_track():
    user = UserFactory()
    track = AudioTrackFactory()
    ListeningProgress.objects.create(
        user=user,
        track=track,
        duration_seconds=track.duration_seconds,
    )

    with pytest.raises(IntegrityError):
        ListeningProgress.objects.create(
            user=user,
            track=track,
            duration_seconds=track.duration_seconds,
        )
