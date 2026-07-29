from datetime import datetime, time, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch

import pytest
from django.utils import timezone

from apps.accounts.tests.factories import UserFactory
from apps.analytics.models import (
    DailyAuthorMetric,
    DailyNarratorMetric,
    DailyPlatformMetric,
    DailyPlaylistMetric,
    DailyTrackMetric,
)
from apps.analytics.services import daily_analytics_aggregation_service
from apps.analytics.tasks import aggregate_daily_analytics
from apps.catalog.tests.factories import AudioTrackFactory
from apps.library.models import PlaybackSession
from apps.playlists.models import PlaylistType, PlaylistVisibility
from apps.playlists.tests.factories import PlaylistFactory, PlaylistItemFactory

pytestmark = pytest.mark.django_db


def session(*, user, track, metric_date, listened, completed=False, hour=1):
    started_at = timezone.make_aware(datetime.combine(metric_date, time(hour=hour)))
    return PlaybackSession.objects.create(
        user=user,
        track=track,
        device_id=f"device-{user.id}-{hour}",
        started_at=started_at,
        last_activity_at=started_at,
        ended_at=started_at,
        listened_seconds=listened,
        completed=completed,
    )


def test_daily_aggregation_builds_privacy_preserving_entity_metrics():
    metric_date = timezone.localdate()
    first_user = UserFactory()
    second_user = UserFactory()
    track = AudioTrackFactory()
    playlist = PlaylistFactory(
        owner=None,
        playlist_type=PlaylistType.EDITORIAL,
        visibility=PlaylistVisibility.PUBLIC,
        is_published=True,
    )
    PlaylistItemFactory(playlist=playlist, track=track, position=1)
    session(
        user=first_user,
        track=track,
        metric_date=metric_date,
        listened=120,
        completed=True,
        hour=1,
    )
    session(
        user=second_user,
        track=track,
        metric_date=metric_date,
        listened=60,
        hour=2,
    )

    daily_analytics_aggregation_service.aggregate(metric_date)

    platform = DailyPlatformMetric.objects.get(date=metric_date)
    assert platform.total_plays == 2
    assert platform.unique_listeners == 2
    assert platform.listening_seconds == Decimal("180")
    assert platform.completed_plays == 1
    track_metric = DailyTrackMetric.objects.get(date=metric_date, track=track)
    assert track_metric.total_plays == 2
    assert (
        DailyAuthorMetric.objects.get(
            date=metric_date, author=track.work.author
        ).total_plays
        == 2
    )
    assert (
        DailyNarratorMetric.objects.get(
            date=metric_date, narrator=track.narrator
        ).total_plays
        == 2
    )
    assert (
        DailyPlaylistMetric.objects.get(date=metric_date, playlist=playlist).total_plays
        == 2
    )
    assert all(
        "user" not in field.name
        for model in (
            DailyPlatformMetric,
            DailyTrackMetric,
            DailyAuthorMetric,
            DailyNarratorMetric,
            DailyPlaylistMetric,
        )
        for field in model._meta.fields
    )


def test_reaggregation_is_idempotent_and_excludes_other_days():
    metric_date = timezone.localdate()
    track = AudioTrackFactory()
    session(
        user=UserFactory(),
        track=track,
        metric_date=metric_date,
        listened=30,
    )
    session(
        user=UserFactory(),
        track=track,
        metric_date=metric_date - timedelta(days=1),
        listened=90,
    )

    daily_analytics_aggregation_service.aggregate(metric_date)
    daily_analytics_aggregation_service.aggregate(metric_date)

    assert DailyPlatformMetric.objects.get(date=metric_date).total_plays == 1
    assert DailyTrackMetric.objects.filter(date=metric_date).count() == 1


def test_celery_task_accepts_explicit_iso_date():
    metric_date = timezone.localdate()
    result = aggregate_daily_analytics(metric_date.isoformat())
    assert result == {"date": metric_date.isoformat(), "totalPlays": 0}


def test_celery_task_defaults_to_yesterday_without_exposing_raw_events():
    target = timezone.localdate() - timedelta(days=1)
    metric = Mock(total_plays=17)

    with patch(
        "apps.analytics.tasks.daily_analytics_aggregation_service.aggregate",
        return_value=metric,
    ) as aggregate:
        result = aggregate_daily_analytics()

    aggregate.assert_called_once_with(target)
    assert result == {"date": target.isoformat(), "totalPlays": 17}
    assert set(result) == {"date", "totalPlays"}
