from datetime import timedelta
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.tests.factories import UserFactory
from apps.analytics.tests.factories import (
    DailyAuthorMetricFactory,
    DailyNarratorMetricFactory,
    DailyPlatformMetricFactory,
    DailyPlaylistMetricFactory,
    DailyTrackMetricFactory,
)

pytestmark = pytest.mark.django_db


def staff_client():
    client = APIClient()
    client.force_authenticate(UserFactory(is_staff=True))
    return client


@pytest.mark.parametrize(
    "url_name",
    ("analytics:summary", "analytics:daily", "analytics:popular"),
)
def test_analytics_endpoints_are_staff_only(url_name):
    url = reverse(url_name)
    anonymous = APIClient().get(url)
    listener = APIClient()
    listener.force_authenticate(UserFactory(is_staff=False))

    assert anonymous.status_code == 401
    assert listener.get(url).status_code == 403


def test_summary_and_daily_endpoints_read_aggregate_rows():
    today = timezone.localdate()
    DailyPlatformMetricFactory(
        date=today - timedelta(days=1),
        total_plays=4,
        unique_listeners=3,
        listening_seconds=3600,
        completed_plays=2,
    )
    DailyPlatformMetricFactory(
        date=today,
        total_plays=6,
        unique_listeners=4,
        listening_seconds=7200,
        completed_plays=3,
    )
    query = {"dateFrom": today - timedelta(days=1), "dateTo": today}

    summary = staff_client().get(reverse("analytics:summary"), query)
    daily = staff_client().get(reverse("analytics:daily"), query)

    assert summary.status_code == 200
    assert summary.data["totalPlays"] == 10
    assert summary.data["uniqueListeners"] == 7
    assert Decimal(str(summary.data["listeningHours"])) == Decimal("3")
    assert Decimal(str(summary.data["completionRate"])) == Decimal("50")
    assert len(daily.data) == 2


def test_popular_endpoint_ranks_all_supported_entities(settings):
    settings.ANALYTICS_PRIVACY_MIN_LISTENERS = 2
    today = timezone.localdate()
    track = DailyTrackMetricFactory(
        date=today,
        total_plays=20,
        unique_listeners=4,
    )
    author = DailyAuthorMetricFactory(date=today, unique_listeners=3)
    narrator = DailyNarratorMetricFactory(date=today, unique_listeners=3)
    playlist = DailyPlaylistMetricFactory(date=today, unique_listeners=3)
    DailyTrackMetricFactory(
        date=today,
        total_plays=100,
        unique_listeners=1,
    )
    low_volume = DailyTrackMetricFactory(
        date=today - timedelta(days=1),
        total_plays=100,
        unique_listeners=1,
    )
    DailyTrackMetricFactory(
        date=today,
        track=low_volume.track,
        total_plays=100,
        unique_listeners=1,
    )

    response = staff_client().get(
        reverse("analytics:popular"),
        {"dateFrom": today - timedelta(days=1), "dateTo": today},
    )

    assert response.status_code == 200
    assert response.data["tracks"][0]["id"] == track.track_id
    assert response.data["authors"][0]["id"] == author.author_id
    assert response.data["narrators"][0]["id"] == narrator.narrator_id
    assert response.data["playlists"][0]["id"] == playlist.playlist_id
    assert len(response.data["tracks"]) == 1


def test_analytics_range_is_bounded(settings):
    settings.ANALYTICS_MAX_RANGE_DAYS = 30
    today = timezone.localdate()
    response = staff_client().get(
        reverse("analytics:summary"),
        {"dateFrom": today - timedelta(days=31), "dateTo": today},
    )
    assert response.status_code == 400
