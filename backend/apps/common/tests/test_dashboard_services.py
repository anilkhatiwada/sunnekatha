from datetime import timedelta
from decimal import Decimal

import pytest
from django.core.cache import cache
from django.utils import timezone

from apps.accounts.tests.factories import UserFactory
from apps.analytics.tests.factories import (
    DailyAuthorMetricFactory,
    DailyNarratorMetricFactory,
    DailyPlatformMetricFactory,
)
from apps.authors.tests.factories import AuthorFactory
from apps.catalog.models import (
    CopyrightLicense,
    CopyrightStatus,
    PermissionDocument,
    RightsHolder,
    RightsPermissionType,
    RightsVerificationStatus,
    TrackProcessingStatus,
    TrackReviewStatus,
)
from apps.catalog.tests.factories import AudioTrackFactory
from apps.common.dashboard_services import (
    ContentSummaryService,
    ListeningSummaryService,
    PendingReviewService,
    PopularAuthorService,
    PopularNarratorService,
    PopularTrackService,
    ProcessingSummaryService,
    RecentPublicationService,
    RecentUploadService,
    RightsWarningService,
    ScheduledPublicationService,
    SubscriptionSummaryService,
    UserSummaryService,
)
from apps.narrators.tests.factories import NarratorFactory
from apps.playlists.tests.factories import PlaylistFactory
from apps.subscriptions.models import SubscriptionStatus
from apps.subscriptions.tests.factories import UserSubscriptionFactory
from apps.uploads.models import UploadSession, UploadStatus, UploadType

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def clear_dashboard_cache():
    cache.clear()
    yield
    cache.clear()


def test_rights_warning_service_reports_only_stored_record_conditions():
    today = timezone.localdate()
    holder = RightsHolder.objects.create(name="Stored Rights Holder")
    expiring = CopyrightLicense.objects.create(
        literary_work=AudioTrackFactory().work,
        rights_holder=holder,
        permission_type=RightsPermissionType.AUDIO,
        expiration_date=today + timedelta(days=20),
        allows_audio=True,
        verification_status=RightsVerificationStatus.VERIFIED,
    )
    PermissionDocument.objects.create(
        license=expiring,
        title="Expiring permission record",
        document="originals/permission-documents/expiring.pdf",
    )
    expired = CopyrightLicense.objects.create(
        literary_work=AudioTrackFactory().work,
        rights_holder=holder,
        permission_type=RightsPermissionType.AUDIO,
        expiration_date=today - timedelta(days=1),
    )
    PermissionDocument.objects.create(
        license=expired,
        title="Expired permission record",
        document="originals/permission-documents/expired.pdf",
    )
    CopyrightLicense.objects.create(
        literary_work=AudioTrackFactory().work,
        rights_holder=holder,
        permission_type=RightsPermissionType.OTHER,
    )
    premium_without_rights = AudioTrackFactory(is_premium=True)
    premium_with_rights = AudioTrackFactory(is_premium=True)
    CopyrightLicense.objects.create(
        literary_work=premium_with_rights.work,
        rights_holder=holder,
        permission_type=RightsPermissionType.COMMERCIAL,
        allows_monetization=True,
        verification_status=RightsVerificationStatus.VERIFIED,
    )
    unresolved = AudioTrackFactory(is_published=True)
    unresolved.work.__class__.objects.exclude(pk=unresolved.work_id).update(
        copyright_status=CopyrightStatus.PERMISSION_GRANTED
    )
    unresolved.work.copyright_status = CopyrightStatus.OWNERSHIP_UNCLEAR
    unresolved.work.save(update_fields=("copyright_status", "updated_at"))

    result = RightsWarningService().get(today=today)

    assert result == {
        "expiring_within_30_days": 1,
        "expired_permissions": 1,
        "missing_documents": 2,
        "premium_without_commercial_rights": 1,
        "published_with_unresolved_copyright": 1,
    }
    assert premium_without_rights.is_premium is True


def test_content_summary_service_returns_catalog_counts():
    AudioTrackFactory(
        is_published=True,
        processing_status=TrackProcessingStatus.READY,
        review_status=TrackReviewStatus.APPROVED,
    )
    AudioTrackFactory(
        is_published=False,
        published_at=None,
        review_status=TrackReviewStatus.DRAFT,
    )
    PlaylistFactory()

    result = ContentSummaryService().get()

    assert result["published_tracks"] == 1
    assert result["draft_tracks"] == 1
    assert result["total_literary_works"] == 2
    assert result["total_authors"] == 2
    assert result["total_narrators"] == 2
    assert result["total_playlists"] == 1


def test_processing_summary_service_returns_counts_and_attention_items():
    failed = AudioTrackFactory(
        is_published=False,
        published_at=None,
        processing_status=TrackProcessingStatus.FAILED,
        review_status=TrackReviewStatus.DRAFT,
    )
    AudioTrackFactory(
        is_published=False,
        published_at=None,
        processing_status=TrackProcessingStatus.PROCESSING,
        review_status=TrackReviewStatus.SUBMITTED,
        submitted_at=timezone.now(),
    )
    service = ProcessingSummaryService()

    summary = service.get()
    attention = service.attention_items()
    failures = service.failed_items()

    assert summary == {
        "processing_tracks": 1,
        "failed_processing_jobs": 1,
        "pending_editorial_reviews": 1,
    }
    assert len(attention) == 2
    assert failed.pk in {item["id"] for item in attention}
    assert [item["id"] for item in failures] == [failed.pk]


def test_user_summary_service_returns_count_and_recent_users():
    older = UserFactory()
    newest = UserFactory()

    service = UserSummaryService()
    assert service.get()["registered_users"] == 2
    assert service.recent(limit=1)[0]["id"] == newest.pk
    assert service.recent(limit=2)[1]["id"] == older.pk


def test_subscription_summary_service_applies_status_and_date_filters():
    now = timezone.now()
    UserSubscriptionFactory(starts_at=now - timedelta(minutes=1))
    UserSubscriptionFactory(
        status=SubscriptionStatus.EXPIRED,
        starts_at=now - timedelta(days=2),
        ends_at=now - timedelta(days=1),
    )

    result = SubscriptionSummaryService().get(now=now)

    assert result["active_premium_subscriptions"] == 1


def test_listening_summary_service_only_uses_current_month():
    month_start = timezone.localdate().replace(day=1)
    DailyPlatformMetricFactory(
        date=month_start,
        listening_seconds=Decimal("7200"),
    )
    DailyPlatformMetricFactory(
        date=month_start - timedelta(days=1),
        listening_seconds=Decimal("36000"),
    )

    result = ListeningSummaryService().get(month_start=month_start)

    assert result == {
        "total_listening_hours": Decimal("2"),
        "analytics_available": True,
    }


def test_pending_review_service_returns_only_submitted_tracks_in_order():
    first = AudioTrackFactory(
        review_status=TrackReviewStatus.SUBMITTED,
        submitted_at=timezone.now() - timedelta(hours=2),
    )
    second = AudioTrackFactory(
        review_status=TrackReviewStatus.SUBMITTED,
        submitted_at=timezone.now() - timedelta(hours=1),
    )
    AudioTrackFactory(review_status=TrackReviewStatus.DRAFT)

    result = PendingReviewService().get()

    assert [item["id"] for item in result] == [first.pk, second.pk]


def test_recent_upload_service_uses_uploader_join_and_compact_values():
    user = UserFactory()
    upload = UploadSession.objects.create(
        user=user,
        upload_type=UploadType.AUDIO_MASTER,
        object_key="originals/audio/test-file.mp3",
        original_filename="test-file.mp3",
        content_type="audio/mpeg",
        expected_size=1024,
        status=UploadStatus.PENDING,
        expires_at=timezone.now() + timedelta(minutes=10),
    )

    result = RecentUploadService().get()

    assert result[0]["id"] == upload.pk
    assert result[0]["uploader"] == user.email
    assert result[0]["upload_type"] == "Audio master"


def test_recent_publication_service_excludes_future_and_unpublished_tracks():
    now = timezone.now()
    published = AudioTrackFactory(published_at=now - timedelta(minutes=1))
    AudioTrackFactory(published_at=now + timedelta(days=1))
    AudioTrackFactory(is_published=False, published_at=None)

    result = RecentPublicationService().get(now=now)

    assert [item["id"] for item in result] == [published.pk]


def test_scheduled_publication_service_returns_future_publications():
    now = timezone.now()
    scheduled = AudioTrackFactory(published_at=now + timedelta(hours=2))
    AudioTrackFactory(published_at=now - timedelta(hours=2))

    result = ScheduledPublicationService().get(now=now)

    assert [item["id"] for item in result] == [scheduled.pk]


def test_popular_track_service_orders_tracks_and_prefetches_genres(
    django_assert_num_queries,
):
    popular = AudioTrackFactory(play_count_cache=50)
    AudioTrackFactory(play_count_cache=10)

    with django_assert_num_queries(2):
        result = PopularTrackService().get()

    assert result[0]["id"] == popular.pk
    assert result[0]["genres"] == ()


def test_popular_author_service_aggregates_current_month_plays():
    month_start = timezone.localdate().replace(day=1)
    popular = AuthorFactory()
    other = AuthorFactory()
    DailyAuthorMetricFactory(author=popular, date=month_start, total_plays=20)
    DailyAuthorMetricFactory(
        author=popular,
        date=month_start + timedelta(days=1),
        total_plays=15,
    )
    DailyAuthorMetricFactory(author=other, date=month_start, total_plays=5)

    result = PopularAuthorService().get(month_start=month_start)

    assert result["analytics_available"] is True
    assert result["items"][0] == {
        "id": popular.pk,
        "name": popular.name_ne,
        "plays": 35,
    }


def test_popular_narrator_service_aggregates_current_month_plays():
    month_start = timezone.localdate().replace(day=1)
    popular = NarratorFactory()
    DailyNarratorMetricFactory(narrator=popular, date=month_start, total_plays=25)

    result = PopularNarratorService().get(month_start=month_start)

    assert result["analytics_available"] is True
    assert result["items"][0] == {
        "id": popular.pk,
        "name": popular.name_ne,
        "plays": 25,
    }


def test_non_personal_metric_cache_is_short_lived_and_request_independent():
    service = UserSummaryService()
    UserFactory()
    assert service.get()["registered_users"] == 1

    UserFactory()
    assert service.get()["registered_users"] == 1

    cache.clear()
    assert service.get()["registered_users"] == 2
