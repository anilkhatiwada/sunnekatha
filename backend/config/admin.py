"""Presentation callbacks for the default Unfold-backed Django admin site."""

from urllib.parse import urlencode

from django.conf import settings
from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone

SIDEBAR_COUNT_TIMEOUT = 60


def admin_model_permission(app_label, model_name):
    """Build an Unfold permission callback for a registered model."""
    permissions = (
        f"{app_label}.view_{model_name}",
        f"{app_label}.change_{model_name}",
    )

    def has_permission(request):
        user = request.user
        return bool(
            user.is_active
            and user.is_staff
            and any(user.has_perm(permission) for permission in permissions)
        )

    return has_permission


def staff_permission(request):
    user = request.user
    return bool(user.is_active and user.is_staff)


def editorial_review_permission(request):
    user = request.user
    return bool(
        user.is_active and user.is_staff and user.has_perm("catalog.approve_audiotrack")
    )


def admin_changelist_url(url_name, **filters):
    """Build a request callback using a named admin URL and encoded filters."""

    def url(request):
        del request
        base_url = reverse(url_name)
        return f"{base_url}?{urlencode(filters)}" if filters else base_url

    return url


def admin_index_url(request):
    del request
    return reverse("admin:index")


def failed_processing_url(request):
    del request
    return reverse("admin:catalog_audioprocessingjob_failed")


def scheduled_publications_url(request):
    del request
    return reverse("admin:catalog_scheduled_publications")


def _cached_badge(request, *, permission, key, count):
    if not permission(request):
        return None
    return cache.get_or_set(key, count, SIDEBAR_COUNT_TIMEOUT)


def processing_queue_badge(request):
    from apps.catalog.models import AudioProcessingJob, AudioProcessingJobStatus

    permission = admin_model_permission("catalog", "audioprocessingjob")
    return _cached_badge(
        request,
        permission=permission,
        key="admin:sidebar:processing-queue:v1",
        count=lambda: AudioProcessingJob.objects.filter(
            status__in=(
                AudioProcessingJobStatus.QUEUED,
                AudioProcessingJobStatus.PROCESSING,
            )
        ).count(),
    )


def failed_processing_badge(request):
    from apps.catalog.models import AudioProcessingJob, AudioProcessingJobStatus

    permission = admin_model_permission("catalog", "audioprocessingjob")
    return _cached_badge(
        request,
        permission=permission,
        key="admin:sidebar:failed-processing:v1",
        count=lambda: AudioProcessingJob.objects.filter(
            status=AudioProcessingJobStatus.FAILED
        ).count(),
    )


def pending_upload_badge(request):
    from apps.uploads.models import UploadSession, UploadStatus

    permission = admin_model_permission("uploads", "uploadsession")
    return _cached_badge(
        request,
        permission=permission,
        key="admin:sidebar:pending-uploads:v1",
        count=lambda: UploadSession.objects.filter(status=UploadStatus.PENDING).count(),
    )


def pending_review_badge(request):
    from apps.catalog.models import PendingReviewTrack, TrackReviewStatus

    return _cached_badge(
        request,
        permission=editorial_review_permission,
        key="admin:sidebar:pending-reviews:v1",
        count=lambda: PendingReviewTrack.objects.filter(
            review_status=TrackReviewStatus.SUBMITTED
        ).count(),
    )


def scheduled_publications_badge(request):
    from apps.catalog.models import AudioTrack

    permission = admin_model_permission("catalog", "audiotrack")
    return _cached_badge(
        request,
        permission=permission,
        key="admin:sidebar:scheduled-publications:v1",
        count=lambda: AudioTrack.objects.filter(
            is_published=True,
            published_at__gt=timezone.now(),
        ).count(),
    )


def _environment():
    environments = {
        "LOCAL": ("LOCAL", "success"),
        "STAGING": ("STAGING", "info"),
        "PRODUCTION": ("PRODUCTION", "warning"),
    }
    return environments.get(settings.ADMIN_ENVIRONMENT, ("LOCAL", "success"))


def environment_callback(request):
    """Return the environment label and Unfold badge variant."""
    del request
    return list(_environment())


def environment_title_prefix_callback(request):
    """Prefix browser titles so similarly branded environments remain distinct."""
    del request
    return f"[{_environment()[0]}] "


def dashboard_callback(request, context):
    """Populate the custom admin homepage with operational data."""
    from apps.common.admin_dashboard import build_dashboard_context

    context.update(build_dashboard_context(request))
    return context
