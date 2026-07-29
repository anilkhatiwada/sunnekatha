from datetime import timedelta

import pytest
from django.contrib.auth.models import Permission
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from apps.accounts.tests.factories import UserFactory
from apps.analytics.dashboard import (
    AnalyticsDateRange,
    admin_analytics_dashboard_service,
)
from apps.analytics.tests.factories import (
    DailyAuthorMetricFactory,
    DailyNarratorMetricFactory,
    DailyPlatformMetricFactory,
    DailyPlaylistMetricFactory,
    DailyTrackMetricFactory,
)

pytestmark = pytest.mark.django_db


def analytics_staff(*codenames):
    user = UserFactory(is_staff=True)
    user.user_permissions.add(
        *Permission.objects.filter(
            content_type__app_label="analytics",
            codename__in=codenames,
        )
    )
    return user


def seed_dashboard_metrics(settings):
    settings.ANALYTICS_PRIVACY_MIN_LISTENERS = 2
    today = timezone.localdate()
    DailyPlatformMetricFactory(
        date=today - timedelta(days=1),
        total_plays=20,
        unique_listeners=8,
        listening_seconds=7200,
        completed_plays=10,
    )
    track = DailyTrackMetricFactory(
        date=today - timedelta(days=1),
        total_plays=20,
        unique_listeners=8,
        listening_seconds=7200,
    )
    author = DailyAuthorMetricFactory(
        date=today - timedelta(days=1),
        author=track.track.work.author,
        total_plays=20,
        unique_listeners=8,
    )
    narrator = DailyNarratorMetricFactory(
        date=today - timedelta(days=1),
        narrator=track.track.narrator,
        total_plays=20,
        unique_listeners=8,
    )
    playlist = DailyPlaylistMetricFactory(
        date=today - timedelta(days=1),
        total_plays=20,
        unique_listeners=8,
    )
    return track, author, narrator, playlist


def test_analytics_dashboard_is_staff_and_permission_only(client):
    url = reverse("admin:analytics_dashboard")
    anonymous = client.get(url)
    staff_without_permission = UserFactory(is_staff=True)
    client.force_login(staff_without_permission)
    denied = client.get(url)
    client.force_login(analytics_staff("view_dailyplatformmetric"))
    allowed = client.get(url)

    assert anonymous.status_code == 302
    assert denied.status_code == 403
    assert allowed.status_code == 200


def test_dashboard_uses_aggregates_shows_rankings_links_and_delay_label(
    client,
    settings,
):
    track, author, narrator, playlist = seed_dashboard_metrics(settings)
    client.force_login(analytics_staff("view_dailyplatformmetric"))

    with CaptureQueriesContext(connection) as queries:
        response = client.get(
            reverse("admin:analytics_dashboard"),
            {"range": "7_days"},
        )

    content = response.content.decode()
    assert response.status_code == 200
    for label in (
        "Listening hours today",
        "Listening hours this week",
        "Listening hours this month",
        "Total plays",
        "Summed daily unique listeners",
        "Completion rate",
        "Most-played tracks",
        "Most-played literary works",
        "Popular authors",
        "Popular narrators",
        "Popular playlists",
        "New users",
        "Premium conversions",
    ):
        assert label in content
    assert "daily aggregate" in content.lower()
    assert "Unavailable" in content
    for value in (
        track.track.title_ne,
        track.track.work.title_ne,
        author.author.name_ne,
        narrator.narrator.name_ne,
        playlist.playlist.title_ne,
    ):
        assert value in content
    assert all(
        "library_playbacksession" not in query["sql"].lower() for query in queries
    )


def test_custom_range_validation_is_clear(client):
    client.force_login(analytics_staff("view_dailyplatformmetric"))

    response = client.get(
        reverse("admin:analytics_dashboard"),
        {"range": "custom", "start": "2026-05-10", "end": "2026-05-01"},
    )

    assert response.status_code == 200
    assert b"Start date cannot be after end date" in response.content
    assert b"Showing the last 30 days" in response.content


def test_csv_export_requires_dedicated_permission_and_contains_no_user_rows(
    client,
    settings,
):
    seed_dashboard_metrics(settings)
    viewer = analytics_staff("view_dailyplatformmetric")
    exporter = analytics_staff(
        "view_dailyplatformmetric",
        "export_analytics_dashboard",
    )
    url = reverse("admin:analytics_dashboard_export")

    client.force_login(viewer)
    denied = client.get(url)
    client.force_login(exporter)
    allowed = client.get(url)

    assert denied.status_code == 403
    assert allowed.status_code == 200
    assert allowed["Content-Type"].startswith("text/csv")
    content = allowed.content.decode()
    assert "SunneKatha aggregate analytics" in content
    assert "Most-played tracks" in content
    assert "@example.com" not in content


def test_sparse_content_is_hidden_by_privacy_threshold(client, settings):
    settings.ANALYTICS_PRIVACY_MIN_LISTENERS = 3
    sparse = DailyTrackMetricFactory(
        date=timezone.localdate(),
        total_plays=100,
        unique_listeners=1,
    )
    client.force_login(analytics_staff("view_dailyplatformmetric"))

    response = client.get(reverse("admin:analytics_dashboard"))

    assert sparse.track.title_ne not in response.content.decode()


def test_dashboard_service_has_fixed_aggregate_query_budget(settings):
    seed_dashboard_metrics(settings)
    today = timezone.localdate()
    date_range = AnalyticsDateRange(
        today - timedelta(days=6),
        today,
        "7_days",
        "Last 7 days",
    )

    with CaptureQueriesContext(connection) as queries:
        result = admin_analytics_dashboard_service.get(date_range=date_range)

    assert len(queries) <= 8
    assert len(result["rankings"]) == 5
    assert all(
        "library_playbacksession" not in query["sql"].lower() for query in queries
    )
