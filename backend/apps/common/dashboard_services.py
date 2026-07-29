"""Query services for the staff dashboard.

The services in this module never inspect a request or a staff user. Admin
permissions remain request-scoped in ``admin_dashboard.py``. Cached results are
therefore limited to non-personal operational aggregates and rankings.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import TypedDict
from uuid import UUID

from django.apps import apps
from django.conf import settings
from django.core.cache import cache
from django.db import DatabaseError
from django.db.models import Count, Exists, OuterRef, Prefetch, Q, Sum
from django.utils import timezone

from apps.catalog.models import TrackProcessingStatus, TrackReviewStatus
from apps.common.admin_status import track_processing_state, upload_processing_state
from apps.subscriptions.models import PlanAccessLevel, SubscriptionStatus

DASHBOARD_TABLE_LIMIT = 6
TRACK_DEFERRED_FIELDS = (
    "transcript",
    "waveform_data",
    "description_ne",
    "description_en",
    "audio_master_file",
    "stream_file_high",
    "stream_file_low",
)


class ContentSummary(TypedDict):
    published_tracks: int
    draft_tracks: int
    total_literary_works: int
    total_authors: int
    total_narrators: int
    total_playlists: int


class ProcessingSummary(TypedDict):
    processing_tracks: int
    failed_processing_jobs: int
    pending_editorial_reviews: int


class UserSummary(TypedDict):
    registered_users: int


class SubscriptionSummary(TypedDict):
    active_premium_subscriptions: int


class ListeningSummary(TypedDict):
    total_listening_hours: Decimal | None
    analytics_available: bool


class RightsWarningSummary(TypedDict):
    expiring_within_30_days: int
    expired_permissions: int
    missing_documents: int
    premium_without_commercial_rights: int
    published_with_unresolved_copyright: int


class TrackDashboardItem(TypedDict):
    id: UUID
    title: str
    narrator: str
    work: str
    processing_status: str
    review_status: str
    submitted_at: datetime | None
    published_at: datetime | None
    updated_at: datetime
    play_count: int
    genres: tuple[str, ...]
    admin_processing_state: str
    processing_job_id: UUID | None
    processing_stage: str
    error_summary: str
    attempts: int
    max_attempts: int


class UploadDashboardItem(TypedDict):
    id: UUID
    filename: str
    uploader: str
    upload_type: str
    status: str
    created_at: datetime
    admin_processing_state: str


class UserDashboardItem(TypedDict):
    id: UUID
    email: str
    display_name: str
    is_active: bool
    created_at: datetime


class PopularEntityItem(TypedDict):
    id: UUID
    name: str
    plays: int


class PopularEntityResult(TypedDict):
    items: list[PopularEntityItem]
    analytics_available: bool


def _cache_timeout() -> int:
    return int(getattr(settings, "ADMIN_DASHBOARD_CACHE_TIMEOUT", 60))


def _cached(key: str, loader):
    """Load a non-personal dashboard value with a short, bounded TTL."""
    value = cache.get(key)
    if value is None:
        value = loader()
        cache.set(key, value, _cache_timeout())
    return value


def _track_queryset(*, include_genres: bool = False):
    AudioTrack = apps.get_model("catalog", "AudioTrack")
    queryset = AudioTrack.objects.select_related(
        "work", "work__author", "narrator", "processing_job"
    ).defer(*TRACK_DEFERRED_FIELDS)
    if include_genres:
        queryset = queryset.prefetch_related("work__genres")
    return queryset


def _track_item(track, *, include_genres: bool = False) -> TrackDashboardItem:
    job = getattr(track, "processing_job", None)
    return {
        "id": track.pk,
        "title": track.title_ne,
        "narrator": track.narrator.name_ne,
        "work": track.work.title_ne,
        "processing_status": track.processing_status,
        "review_status": track.review_status,
        "submitted_at": track.submitted_at,
        "published_at": track.published_at,
        "updated_at": track.updated_at,
        "play_count": track.play_count_cache,
        "genres": (
            tuple(genre.name_ne for genre in track.work.genres.all())
            if include_genres
            else ()
        ),
        "admin_processing_state": track_processing_state(track),
        "processing_job_id": job.pk if job else None,
        "processing_stage": job.get_stage_display() if job else "—",
        "error_summary": (
            job.error_summary
            if job and job.error_summary
            else "No error summary recorded."
        ),
        "attempts": job.attempts if job else 0,
        "max_attempts": job.max_attempts if job else 0,
    }


class ContentSummaryService:
    """Counts describing the catalog; result is non-personal and cached."""

    cache_key = "admin-dashboard:content-summary:v1"

    def get(self, *, now: datetime | None = None) -> ContentSummary:
        now = now or timezone.now()

        def load() -> ContentSummary:
            AudioTrack = apps.get_model("catalog", "AudioTrack")
            counts = AudioTrack.objects.aggregate(
                published_tracks=Count(
                    "id",
                    filter=Q(
                        is_published=True,
                        processing_status=TrackProcessingStatus.READY,
                        published_at__lte=now,
                    ),
                ),
                draft_tracks=Count(
                    "id", filter=Q(review_status=TrackReviewStatus.DRAFT)
                ),
            )
            return {
                **counts,
                "total_literary_works": apps.get_model(
                    "catalog", "LiteraryWork"
                ).objects.count(),
                "total_authors": apps.get_model("authors", "Author").objects.count(),
                "total_narrators": apps.get_model(
                    "narrators", "Narrator"
                ).objects.count(),
                "total_playlists": apps.get_model(
                    "playlists", "Playlist"
                ).objects.count(),
            }

        return _cached(f"{self.cache_key}:{now.date().isoformat()}", load)


class ProcessingSummaryService:
    """Processing counts and the compact operational queues."""

    cache_key = "admin-dashboard:processing-summary:v1"

    def get(self) -> ProcessingSummary:
        def load() -> ProcessingSummary:
            AudioTrack = apps.get_model("catalog", "AudioTrack")
            return AudioTrack.objects.aggregate(
                processing_tracks=Count(
                    "id",
                    filter=Q(processing_status=TrackProcessingStatus.PROCESSING),
                ),
                failed_processing_jobs=Count(
                    "id", filter=Q(processing_status=TrackProcessingStatus.FAILED)
                ),
                pending_editorial_reviews=Count(
                    "id", filter=Q(review_status=TrackReviewStatus.SUBMITTED)
                ),
            )

        return _cached(self.cache_key, load)

    def attention_items(
        self, *, limit: int = DASHBOARD_TABLE_LIMIT
    ) -> list[TrackDashboardItem]:
        tracks = (
            _track_queryset()
            .filter(
                Q(processing_status=TrackProcessingStatus.FAILED)
                | Q(review_status=TrackReviewStatus.SUBMITTED)
            )
            .order_by("-updated_at")[:limit]
        )
        return [_track_item(track) for track in tracks]

    def failed_items(
        self, *, limit: int = DASHBOARD_TABLE_LIMIT
    ) -> list[TrackDashboardItem]:
        tracks = (
            _track_queryset()
            .filter(processing_status=TrackProcessingStatus.FAILED)
            .order_by("-updated_at")[:limit]
        )
        return [_track_item(track) for track in tracks]


class UserSummaryService:
    """User count and recent registrations; no staff identity is cached."""

    cache_key = "admin-dashboard:user-summary:v1"

    def get(self) -> UserSummary:
        def load() -> UserSummary:
            User = apps.get_model("accounts", "User")
            return {"registered_users": User.objects.count()}

        return _cached(self.cache_key, load)

    def recent(self, *, limit: int = DASHBOARD_TABLE_LIMIT) -> list[UserDashboardItem]:
        User = apps.get_model("accounts", "User")
        users = User.objects.only(
            "id", "email", "display_name", "is_active", "created_at"
        ).order_by("-created_at")[:limit]
        return [
            {
                "id": user.pk,
                "email": user.email,
                "display_name": user.display_name,
                "is_active": user.is_active,
                "created_at": user.created_at,
            }
            for user in users
        ]


class SubscriptionSummaryService:
    """Current premium entitlement counts, cached without request data."""

    cache_key = "admin-dashboard:subscription-summary:v1"

    def get(self, *, now: datetime | None = None) -> SubscriptionSummary:
        now = now or timezone.now()

        def load() -> SubscriptionSummary:
            UserSubscription = apps.get_model("subscriptions", "UserSubscription")
            current_statuses = (
                SubscriptionStatus.ACTIVE,
                SubscriptionStatus.TRIAL,
                SubscriptionStatus.STAFF_GRANTED,
            )
            count = (
                UserSubscription.objects.select_related("plan")
                .filter(
                    status__in=current_statuses,
                    starts_at__lte=now,
                    plan__access_level=PlanAccessLevel.PREMIUM,
                    plan__allows_premium_streaming=True,
                )
                .filter(Q(ends_at__isnull=True) | Q(ends_at__gt=now))
                .count()
            )
            return {"active_premium_subscriptions": count}

        return _cached(f"{self.cache_key}:{now.date().isoformat()}", load)


class ListeningSummaryService:
    """Monthly listening total from daily aggregates."""

    cache_key = "admin-dashboard:listening-summary:v1"

    def get(self, *, month_start: date | None = None) -> ListeningSummary:
        month_start = month_start or timezone.localdate().replace(day=1)
        period_end = timezone.localdate()

        def load() -> ListeningSummary:
            try:
                DailyPlatformMetric = apps.get_model("analytics", "DailyPlatformMetric")
                seconds = DailyPlatformMetric.objects.filter(
                    date__range=(month_start, period_end)
                ).aggregate(total=Sum("listening_seconds"))["total"] or Decimal("0")
            except (LookupError, DatabaseError):
                return {
                    "total_listening_hours": None,
                    "analytics_available": False,
                }
            return {
                "total_listening_hours": seconds / Decimal("3600"),
                "analytics_available": True,
            }

        return _cached(f"{self.cache_key}:{month_start.isoformat()}", load)


class PendingReviewService:
    def get(self, *, limit: int = DASHBOARD_TABLE_LIMIT) -> list[TrackDashboardItem]:
        tracks = (
            _track_queryset()
            .filter(review_status=TrackReviewStatus.SUBMITTED)
            .order_by("submitted_at", "id")[:limit]
        )
        return [_track_item(track) for track in tracks]


class RightsWarningService:
    """Factual warnings from stored rights records; no legal conclusions."""

    cache_key = "admin-dashboard:rights-warnings:v1"

    def get(self, *, today: date | None = None) -> RightsWarningSummary:
        today = today or timezone.localdate()

        def load() -> RightsWarningSummary:
            CopyrightLicense = apps.get_model("catalog", "CopyrightLicense")
            AudioTrack = apps.get_model("catalog", "AudioTrack")
            active_commercial = CopyrightLicense.objects.filter(
                literary_work_id=OuterRef("work_id"),
                allows_monetization=True,
                verification_status="verified",
            ).filter(
                Q(effective_date__isnull=True) | Q(effective_date__lte=today),
                Q(expiration_date__isnull=True) | Q(expiration_date__gte=today),
            )
            unresolved = (
                "permission_pending",
                "permission_expired",
                "permission_rejected",
                "ownership_unclear",
                "unknown",
            )
            licenses = CopyrightLicense.objects.all()
            license_counts = licenses.aggregate(
                expiring_within_30_days=Count(
                    "id",
                    filter=Q(
                        expiration_date__gte=today,
                        expiration_date__lte=today + timedelta(days=30),
                    ),
                    distinct=True,
                ),
                expired_permissions=Count(
                    "id",
                    filter=(
                        Q(expiration_date__lt=today)
                        | Q(literary_work__copyright_status=("permission_expired"))
                    ),
                    distinct=True,
                ),
                missing_documents=Count(
                    "id",
                    filter=Q(documents__isnull=True),
                    distinct=True,
                ),
            )
            track_counts = AudioTrack.objects.annotate(
                has_commercial_rights=Exists(active_commercial)
            ).aggregate(
                premium_without_commercial_rights=Count(
                    "id",
                    filter=Q(
                        is_premium=True,
                        has_commercial_rights=False,
                    ),
                ),
                published_with_unresolved_copyright=Count(
                    "id",
                    filter=Q(
                        is_published=True,
                        work__copyright_status__in=unresolved,
                    ),
                    distinct=True,
                ),
            )
            return {
                **license_counts,
                **track_counts,
            }

        return _cached(f"{self.cache_key}:{today.isoformat()}", load)


class RecentUploadService:
    def get(self, *, limit: int = DASHBOARD_TABLE_LIMIT) -> list[UploadDashboardItem]:
        UploadSession = apps.get_model("uploads", "UploadSession")
        AudioProcessingJob = apps.get_model("catalog", "AudioProcessingJob")
        uploads = (
            UploadSession.objects.select_related("user")
            .prefetch_related(
                Prefetch(
                    "processing_jobs",
                    queryset=AudioProcessingJob.objects.select_related(
                        "track"
                    ).order_by("-updated_at"),
                    to_attr="_prefetched_processing_jobs",
                )
            )
            .only(
                "id",
                "original_filename",
                "upload_type",
                "status",
                "created_at",
                "user__id",
                "user__email",
            )
            .order_by("-created_at")[:limit]
        )
        return [
            {
                "id": upload.pk,
                "filename": upload.original_filename,
                "uploader": upload.user.email,
                "upload_type": upload.get_upload_type_display(),
                "status": upload.get_status_display(),
                "created_at": upload.created_at,
                "admin_processing_state": upload_processing_state(upload),
            }
            for upload in uploads
        ]


class RecentPublicationService:
    def get(
        self,
        *,
        now: datetime | None = None,
        limit: int = DASHBOARD_TABLE_LIMIT,
    ) -> list[TrackDashboardItem]:
        now = now or timezone.now()
        tracks = (
            _track_queryset()
            .filter(
                is_published=True,
                processing_status=TrackProcessingStatus.READY,
                published_at__lte=now,
            )
            .order_by("-published_at")[:limit]
        )
        return [_track_item(track) for track in tracks]


class ScheduledPublicationService:
    def get(
        self,
        *,
        now: datetime | None = None,
        limit: int = DASHBOARD_TABLE_LIMIT,
    ) -> list[TrackDashboardItem]:
        now = now or timezone.now()
        tracks = (
            _track_queryset()
            .filter(is_published=True, published_at__gt=now)
            .order_by("published_at")[:limit]
        )
        return [_track_item(track) for track in tracks]


class PopularTrackService:
    """Published track ranking; cached because it is global and non-personal."""

    cache_key = "admin-dashboard:popular-tracks:v1"

    def get(
        self,
        *,
        now: datetime | None = None,
        limit: int = DASHBOARD_TABLE_LIMIT,
    ) -> list[TrackDashboardItem]:
        now = now or timezone.now()

        def load() -> list[TrackDashboardItem]:
            tracks = (
                _track_queryset(include_genres=True)
                .filter(
                    is_published=True,
                    processing_status=TrackProcessingStatus.READY,
                    published_at__lte=now,
                )
                .order_by("-play_count_cache", "-published_at")[:limit]
            )
            return [_track_item(track, include_genres=True) for track in tracks]

        key = f"{self.cache_key}:{now.date().isoformat()}:{limit}"
        return _cached(key, load)


class _PopularEntityService:
    model_name = ""
    relation_name = ""
    cache_key = ""

    def get(
        self,
        *,
        month_start: date | None = None,
        limit: int = DASHBOARD_TABLE_LIMIT,
    ) -> PopularEntityResult:
        month_start = month_start or timezone.localdate().replace(day=1)
        period_end = timezone.localdate()

        def load() -> PopularEntityResult:
            try:
                Metric = apps.get_model("analytics", self.model_name)
                id_field = f"{self.relation_name}_id"
                name_field = f"{self.relation_name}__name_ne"
                rows = list(
                    Metric.objects.filter(date__range=(month_start, period_end))
                    .values(id_field, name_field)
                    .annotate(plays=Sum("total_plays"))
                    .order_by("-plays", name_field)[:limit]
                )
            except (LookupError, DatabaseError):
                return {"items": [], "analytics_available": False}
            return {
                "items": [
                    {
                        "id": row[id_field],
                        "name": row[name_field],
                        "plays": row["plays"] or 0,
                    }
                    for row in rows
                ],
                "analytics_available": True,
            }

        key = f"{self.cache_key}:{month_start.isoformat()}:{limit}"
        return _cached(key, load)


class PopularAuthorService(_PopularEntityService):
    model_name = "DailyAuthorMetric"
    relation_name = "author"
    cache_key = "admin-dashboard:popular-authors:v1"


class PopularNarratorService(_PopularEntityService):
    model_name = "DailyNarratorMetric"
    relation_name = "narrator"
    cache_key = "admin-dashboard:popular-narrators:v1"


content_summary_service = ContentSummaryService()
processing_summary_service = ProcessingSummaryService()
user_summary_service = UserSummaryService()
subscription_summary_service = SubscriptionSummaryService()
listening_summary_service = ListeningSummaryService()
pending_review_service = PendingReviewService()
rights_warning_service = RightsWarningService()
recent_upload_service = RecentUploadService()
recent_publication_service = RecentPublicationService()
scheduled_publication_service = ScheduledPublicationService()
popular_track_service = PopularTrackService()
popular_author_service = PopularAuthorService()
popular_narrator_service = PopularNarratorService()
