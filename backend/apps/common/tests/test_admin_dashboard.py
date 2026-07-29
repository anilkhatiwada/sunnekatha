import pytest
from django.contrib.auth.models import Permission
from django.core.cache import cache
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.analytics.tests.factories import DailyPlatformMetricFactory
from apps.catalog.models import (
    TrackProcessingStatus,
    TrackReviewStatus,
)
from apps.catalog.tests.factories import AudioTrackFactory
from apps.common import admin_dashboard
from apps.common.admin_dashboard import build_dashboard_context
from apps.subscriptions.tests.factories import UserSubscriptionFactory


@pytest.fixture(autouse=True)
def clear_dashboard_cache():
    cache.clear()
    yield
    cache.clear()


def _superuser(email="dashboard-admin@example.com"):
    return User.objects.create_superuser(
        email=email,
        username=email.split("@", 1)[0],
        display_name="Dashboard Admin",
        password="a-secure-test-password",
    )


def test_anonymous_dashboard_access_redirects_to_login(client):
    response = client.get(reverse("admin:index"))

    assert response.status_code == 302
    assert reverse("admin:login") in response.url


@pytest.mark.django_db
def test_dashboard_renders_all_metrics_sections_links_and_empty_states(client):
    client.force_login(_superuser())

    response = client.get(reverse("admin:index"))

    assert response.status_code == 200
    assert len(response.context["dashboard_metrics"]) == 12
    assert len(response.context["dashboard_sections"]) == 11
    assert all(
        metric["url"].startswith("/admin/")
        for metric in response.context["dashboard_metrics"]
    )
    assert b"Total published tracks" in response.content
    assert b"Tracks requiring attention" in response.content
    assert b"No upload sessions have been created." in response.content
    assert b"Upcoming scheduled publications" in response.content
    assert response.content.count(b"<h1") == 1


@pytest.mark.django_db
def test_dashboard_hides_models_without_staff_permissions(client):
    staff_user = User.objects.create_user(
        email="author-dashboard@example.com",
        username="author-dashboard",
        display_name="Author Dashboard",
        password="a-secure-test-password",
        is_staff=True,
    )
    staff_user.user_permissions.add(
        Permission.objects.get(
            content_type__app_label="authors",
            codename="view_author",
        )
    )
    client.force_login(staff_user)

    response = client.get(reverse("admin:index"))

    assert response.status_code == 200
    assert [metric["label"] for metric in response.context["dashboard_metrics"]] == [
        "Total authors"
    ]
    assert response.context["dashboard_sections"] == []
    assert b"Registered users" not in response.content


@pytest.mark.django_db
def test_dashboard_metrics_use_existing_operational_data(rf):
    admin_user = _superuser("metric-admin@example.com")
    request = rf.get("/admin/")
    request.user = admin_user
    AudioTrackFactory(
        is_published=True,
        processing_status=TrackProcessingStatus.READY,
        review_status=TrackReviewStatus.APPROVED,
        play_count_cache=20,
    )
    AudioTrackFactory(
        is_published=False,
        published_at=None,
        processing_status=TrackProcessingStatus.PROCESSING,
        review_status=TrackReviewStatus.DRAFT,
    )
    AudioTrackFactory(
        is_published=False,
        published_at=None,
        processing_status=TrackProcessingStatus.FAILED,
        review_status=TrackReviewStatus.SUBMITTED,
        submitted_at=timezone.now(),
    )
    UserSubscriptionFactory()
    DailyPlatformMetricFactory(
        date=timezone.localdate(),
        listening_seconds=7200,
    )

    context = build_dashboard_context(request)
    metrics = {
        metric["label"]: metric["value"] for metric in context["dashboard_metrics"]
    }

    assert metrics["Total published tracks"] == 1
    assert metrics["Draft tracks"] == 1
    assert metrics["Tracks processing"] == 1
    assert metrics["Failed processing jobs"] == 1
    assert metrics["Pending editorial reviews"] == 1
    assert metrics["Active premium subscriptions"] == 1
    assert metrics["Total listening hours this month"] == "2.0"


@pytest.mark.django_db
def test_dashboard_query_count_is_fixed_and_heavy_track_fields_are_deferred(
    rf,
    django_assert_max_num_queries,
):
    admin_user = _superuser("query-dashboard@example.com")
    request = rf.get("/admin/")
    request.user = admin_user
    AudioTrackFactory.create_batch(
        8,
        transcript="A transcript that must not be loaded.",
        waveform_data=[0.1, 0.4, 0.2],
    )

    with CaptureQueriesContext(connection) as captured:
        with django_assert_max_num_queries(22):
            context = build_dashboard_context(request)

    sql = "\n".join(query["sql"].lower() for query in captured.captured_queries)
    assert len(context["dashboard_sections"]) == 11
    assert '"transcript"' not in sql
    assert '"waveform_data"' not in sql


@pytest.mark.django_db
def test_dashboard_handles_missing_analytics_models(rf, monkeypatch):
    admin_user = _superuser("analytics-dashboard@example.com")
    request = rf.get("/admin/")
    request.user = admin_user
    unavailable = {
        "items": [],
        "analytics_available": False,
    }
    monkeypatch.setattr(
        admin_dashboard.listening_summary_service,
        "get",
        lambda **kwargs: {
            "total_listening_hours": None,
            "analytics_available": False,
        },
    )
    monkeypatch.setattr(
        admin_dashboard.popular_author_service,
        "get",
        lambda **kwargs: unavailable,
    )
    monkeypatch.setattr(
        admin_dashboard.popular_narrator_service,
        "get",
        lambda **kwargs: unavailable,
    )

    context = build_dashboard_context(request)
    metrics = {
        metric["label"]: metric["value"] for metric in context["dashboard_metrics"]
    }
    sections = {
        section["identifier"]: section for section in context["dashboard_sections"]
    }

    assert metrics["Total listening hours this month"] == "—"
    assert context["dashboard_analytics_available"] is False
    assert (
        sections["popular-authors"]["empty_state"]
        == "Author analytics are temporarily unavailable."
    )
    assert (
        sections["popular-narrators"]["empty_state"]
        == "Narrator analytics are temporarily unavailable."
    )
