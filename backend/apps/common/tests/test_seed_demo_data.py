from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings

from apps.accounts.models import User
from apps.authors.models import Author
from apps.catalog.models import AudioTrack
from apps.common.management.commands.seed_demo_data import (
    DEMO_AUTHOR_SLUGS,
    DEMO_EMAILS,
    DEMO_PASSWORD,
    DEMO_TRACK_SLUGS,
)
from apps.home.models import HomeSection
from apps.library.models import FavoriteTrack, ListeningProgress
from apps.playlists.models import Playlist
from apps.subscriptions.models import UserSubscription

pytestmark = pytest.mark.django_db


def run_seed(*args):
    output = StringIO()
    call_command("seed_demo_data", *args, stdout=output)
    return output.getvalue()


@override_settings(DEBUG=True)
def test_seed_demo_data_creates_realistic_connected_demo_records():
    output = run_seed()

    assert User.objects.filter(email__in=DEMO_EMAILS).count() == len(DEMO_EMAILS)
    assert Author.objects.filter(slug__in=DEMO_AUTHOR_SLUGS).count() == len(
        DEMO_AUTHOR_SLUGS
    )
    assert AudioTrack.objects.filter(slug__in=DEMO_TRACK_SLUGS).count() == len(
        DEMO_TRACK_SLUGS
    )
    assert Playlist.objects.filter(is_featured=True, is_published=True).count() >= 2
    assert HomeSection.objects.filter(identifier__startswith="demo-").count() == 7
    assert FavoriteTrack.objects.exists()
    assert ListeningProgress.objects.exists()
    assert UserSubscription.objects.exists()
    assert not AudioTrack.objects.exclude(audio_master_file="").exists()
    assert DEMO_PASSWORD in output
    assert "development" in output.lower()


@override_settings(DEBUG=True)
def test_seed_demo_data_is_idempotent_and_clear_is_scoped():
    run_seed()
    counts = {
        "users": User.objects.count(),
        "tracks": AudioTrack.objects.count(),
        "sections": HomeSection.objects.count(),
    }
    unrelated_author = Author.objects.create(
        slug="unrelated-author",
        name_ne="असम्बन्धित लेखक",
    )

    run_seed()
    assert User.objects.count() == counts["users"]
    assert AudioTrack.objects.count() == counts["tracks"]
    assert HomeSection.objects.count() == counts["sections"]

    run_seed("--clear-existing-data")
    assert Author.objects.filter(pk=unrelated_author.pk).exists()
    assert User.objects.filter(email__in=DEMO_EMAILS).count() == len(DEMO_EMAILS)


def test_seed_demo_data_refuses_non_debug_environment():
    with pytest.raises(CommandError, match="development-only"):
        run_seed()
