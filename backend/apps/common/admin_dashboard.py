"""Permission-aware presentation assembly for the admin dashboard."""

from urllib.parse import urlencode

from django.urls import NoReverseMatch, reverse
from django.utils import timezone

from apps.catalog.models import TrackProcessingStatus, TrackReviewStatus
from apps.common.admin_status import processing_state_badge
from apps.common.dashboard_services import (
    content_summary_service,
    listening_summary_service,
    pending_review_service,
    popular_author_service,
    popular_narrator_service,
    popular_track_service,
    processing_summary_service,
    recent_publication_service,
    recent_upload_service,
    rights_warning_service,
    scheduled_publication_service,
    subscription_summary_service,
    user_summary_service,
)
from apps.subscriptions.models import SubscriptionStatus


def _can_view(user, app_label, model_name):
    return user.has_perm(f"{app_label}.view_{model_name}") or user.has_perm(
        f"{app_label}.change_{model_name}"
    )


def _admin_url(app_label, model_name, *, filters=None, object_id=None):
    suffix = "change" if object_id is not None else "changelist"
    try:
        url = reverse(
            f"admin:{app_label}_{model_name}_{suffix}",
            args=(object_id,) if object_id is not None else None,
        )
    except NoReverseMatch:
        return reverse("admin:index")
    return f"{url}?{urlencode(filters)}" if filters else url


def _format_datetime(value):
    return timezone.localtime(value).strftime("%b %d, %Y · %H:%M") if value else "—"


def _metric(label, value, icon, url):
    return {"label": label, "value": value, "icon": icon, "url": url}


def _section(identifier, title, columns, rows, empty_state, view_all_url):
    return {
        "identifier": identifier,
        "title": title,
        "columns": columns,
        "rows": rows,
        "empty_state": empty_state,
        "view_all_url": view_all_url,
    }


def _track_row(item, *, detail, value):
    return {
        "url": _admin_url("catalog", "audiotrack", object_id=item["id"]),
        "cells": (item["title"], item["narrator"], detail, value),
    }


def _attention_label(item):
    if item["processing_status"] == TrackProcessingStatus.FAILED:
        return "Processing failed"
    if item["review_status"] == TrackReviewStatus.SUBMITTED:
        return "Editorial review"
    return item["processing_status"].replace("_", " ").title()


def build_dashboard_context(request):
    """Compose service results that this staff user is allowed to view."""
    user = request.user
    now = timezone.now()
    month_start = timezone.localdate().replace(day=1)
    metrics = []
    sections = []

    permissions = {
        "tracks": _can_view(user, "catalog", "audiotrack"),
        "works": _can_view(user, "catalog", "literarywork"),
        "authors": _can_view(user, "authors", "author"),
        "narrators": _can_view(user, "narrators", "narrator"),
        "playlists": _can_view(user, "playlists", "playlist"),
        "uploads": _can_view(user, "uploads", "uploadsession"),
        "users": _can_view(user, "accounts", "user"),
        "subscriptions": _can_view(user, "subscriptions", "usersubscription"),
        "platform_analytics": _can_view(user, "analytics", "dailyplatformmetric"),
        "author_analytics": _can_view(user, "analytics", "dailyauthormetric"),
        "narrator_analytics": _can_view(user, "analytics", "dailynarratormetric"),
        "rights": _can_view(user, "catalog", "copyrightlicense"),
    }

    if any(
        permissions[key]
        for key in ("tracks", "works", "authors", "narrators", "playlists")
    ):
        content = content_summary_service.get(now=now)
        content_metrics = (
            (
                "tracks",
                "Total published tracks",
                content["published_tracks"],
                "library_music",
                ("catalog", "audiotrack", {"is_published__exact": "1"}),
            ),
            (
                "tracks",
                "Draft tracks",
                content["draft_tracks"],
                "draft",
                (
                    "catalog",
                    "audiotrack",
                    {"review_status__exact": TrackReviewStatus.DRAFT},
                ),
            ),
            (
                "works",
                "Total literary works",
                content["total_literary_works"],
                "menu_book",
                ("catalog", "literarywork", None),
            ),
            (
                "authors",
                "Total authors",
                content["total_authors"],
                "person",
                ("authors", "author", None),
            ),
            (
                "narrators",
                "Total narrators",
                content["total_narrators"],
                "record_voice_over",
                ("narrators", "narrator", None),
            ),
            (
                "playlists",
                "Total playlists",
                content["total_playlists"],
                "queue_music",
                ("playlists", "playlist", None),
            ),
        )
        for permission, label, value, icon, (app, model, filters) in content_metrics:
            if permissions[permission]:
                metrics.append(
                    _metric(label, value, icon, _admin_url(app, model, filters=filters))
                )

    if permissions["rights"]:
        warnings = rights_warning_service.get(today=now.date())
        warning_rows = (
            (
                "Permissions expiring within 30 days",
                warnings["expiring_within_30_days"],
                _admin_url(
                    "catalog",
                    "copyrightlicense",
                    filters={"expiring_soon": "yes"},
                ),
            ),
            (
                "Expired permissions",
                warnings["expired_permissions"],
                _admin_url(
                    "catalog",
                    "copyrightlicense",
                    filters={"expired": "yes"},
                ),
            ),
            (
                "Missing permission documents",
                warnings["missing_documents"],
                _admin_url(
                    "catalog",
                    "copyrightlicense",
                    filters={"missing_documents": "yes"},
                ),
            ),
            (
                "Premium tracks without stored commercial rights",
                warnings["premium_without_commercial_rights"],
                _admin_url(
                    "catalog",
                    "audiotrack",
                    filters={"is_premium__exact": "1"},
                ),
            ),
            (
                "Published tracks with unresolved copyright status",
                warnings["published_with_unresolved_copyright"],
                _admin_url(
                    "catalog",
                    "audiotrack",
                    filters={"is_published__exact": "1"},
                ),
            ),
        )
        sections.append(
            _section(
                "rights-warnings",
                "Rights record warnings",
                ("Stored-record warning", "Count"),
                [
                    {"url": url, "cells": (label, f"{count:,}")}
                    for label, count, url in warning_rows
                ],
                "No rights record warnings are currently present.",
                _admin_url("catalog", "copyrightlicense"),
            )
        )

    if permissions["tracks"]:
        processing = processing_summary_service.get()
        metrics.extend(
            (
                _metric(
                    "Tracks processing",
                    processing["processing_tracks"],
                    "sync",
                    _admin_url(
                        "catalog",
                        "audiotrack",
                        filters={
                            "processing_status__exact": (
                                TrackProcessingStatus.PROCESSING
                            )
                        },
                    ),
                ),
                _metric(
                    "Failed processing jobs",
                    processing["failed_processing_jobs"],
                    "error",
                    _admin_url(
                        "catalog",
                        "audioprocessingjob",
                        filters={"processing_state": "failed"},
                    ),
                ),
            )
        )
        attention = processing_summary_service.attention_items()
        sections.append(
            _section(
                "tracks-requiring-attention",
                "Tracks requiring attention",
                ("Track", "Narrator", "Issue", "Updated"),
                [
                    _track_row(
                        item,
                        detail=processing_state_badge(item["admin_processing_state"]),
                        value=_format_datetime(item["updated_at"]),
                    )
                    for item in attention
                ],
                "No tracks currently require attention.",
                _admin_url("catalog", "audiotrack"),
            )
        )
        recent = recent_publication_service.get(now=now)
        sections.append(
            _section(
                "recent-publications",
                "Recent publications",
                ("Track", "Narrator", "Work", "Published"),
                [
                    _track_row(
                        item,
                        detail=item["work"],
                        value=_format_datetime(item["published_at"]),
                    )
                    for item in recent
                ],
                "No tracks have been published yet.",
                _admin_url(
                    "catalog", "audiotrack", filters={"is_published__exact": "1"}
                ),
            )
        )
        failed = processing_summary_service.failed_items()
        sections.append(
            _section(
                "failed-processing",
                "Failed audio processing jobs",
                ("Track", "Stage", "Error summary", "Attempts"),
                [
                    {
                        "url": (
                            _admin_url(
                                "catalog",
                                "audioprocessingjob",
                                object_id=item["processing_job_id"],
                            )
                            if item["processing_job_id"]
                            else _admin_url(
                                "catalog",
                                "audiotrack",
                                object_id=item["id"],
                            )
                        ),
                        "cells": (
                            item["title"],
                            item["processing_stage"],
                            item["error_summary"],
                            (
                                f"{item['attempts']} / {item['max_attempts']}"
                                if item["max_attempts"]
                                else "—"
                            ),
                        ),
                    }
                    for item in failed
                ],
                "No failed audio processing jobs.",
                _admin_url(
                    "catalog",
                    "audioprocessingjob",
                    filters={"processing_state": "failed"},
                ),
            )
        )
        pending = pending_review_service.get()
        metrics.append(
            _metric(
                "Pending editorial reviews",
                processing["pending_editorial_reviews"],
                "rate_review",
                _admin_url("catalog", "pendingreviewtrack"),
            )
        )
        sections.append(
            _section(
                "pending-reviews",
                "Pending content reviews",
                ("Track", "Narrator", "Work", "Submitted"),
                [
                    _track_row(
                        item,
                        detail=item["work"],
                        value=_format_datetime(item["submitted_at"]),
                    )
                    for item in pending
                ],
                "No content is waiting for editorial review.",
                _admin_url("catalog", "pendingreviewtrack"),
            )
        )
        popular = popular_track_service.get(now=now)
        sections.append(
            _section(
                "most-played",
                "Most-played tracks",
                ("Track", "Narrator", "Work", "Plays"),
                [
                    _track_row(
                        item,
                        detail=item["work"],
                        value=f"{item['play_count']:,}",
                    )
                    for item in popular
                ],
                "No published track play data is available.",
                _admin_url(
                    "catalog", "audiotrack", filters={"is_published__exact": "1"}
                ),
            )
        )
        scheduled = scheduled_publication_service.get(now=now)
        sections.append(
            _section(
                "upcoming-publications",
                "Upcoming scheduled publications",
                ("Track", "Narrator", "Work", "Scheduled"),
                [
                    _track_row(
                        item,
                        detail=item["work"],
                        value=_format_datetime(item["published_at"]),
                    )
                    for item in scheduled
                ],
                "No publications are currently scheduled.",
                _admin_url(
                    "catalog",
                    "audiotrack",
                    filters={
                        "is_published__exact": "1",
                        "published_at__gt": now.isoformat(),
                    },
                ),
            )
        )

    if permissions["uploads"]:
        uploads = recent_upload_service.get()
        sections.append(
            _section(
                "recent-uploads",
                "Recent uploads",
                ("File", "Uploader", "Type", "Status"),
                [
                    {
                        "url": _admin_url(
                            "uploads", "uploadsession", object_id=item["id"]
                        ),
                        "cells": (
                            item["filename"],
                            item["uploader"],
                            item["upload_type"],
                            processing_state_badge(item["admin_processing_state"]),
                        ),
                    }
                    for item in uploads
                ],
                "No upload sessions have been created.",
                _admin_url("uploads", "uploadsession"),
            )
        )

    if permissions["users"]:
        users = user_summary_service.get()
        metrics.append(
            _metric(
                "Registered users",
                users["registered_users"],
                "group",
                _admin_url("accounts", "user"),
            )
        )
        recent_users = user_summary_service.recent()
        sections.append(
            _section(
                "recent-users",
                "Recently registered users",
                ("User", "Display name", "Status", "Registered"),
                [
                    {
                        "url": _admin_url("accounts", "user", object_id=item["id"]),
                        "cells": (
                            item["email"],
                            item["display_name"] or "—",
                            "Active" if item["is_active"] else "Inactive",
                            _format_datetime(item["created_at"]),
                        ),
                    }
                    for item in recent_users
                ],
                "No users have registered yet.",
                _admin_url("accounts", "user"),
            )
        )

    if permissions["subscriptions"]:
        subscription = subscription_summary_service.get(now=now)
        statuses = (
            SubscriptionStatus.ACTIVE,
            SubscriptionStatus.TRIAL,
            SubscriptionStatus.STAFF_GRANTED,
        )
        metrics.append(
            _metric(
                "Active premium subscriptions",
                subscription["active_premium_subscriptions"],
                "workspace_premium",
                _admin_url(
                    "subscriptions",
                    "usersubscription",
                    filters={"status__in": ",".join(statuses)},
                ),
            )
        )

    analytics_available = True
    if permissions["platform_analytics"]:
        listening = listening_summary_service.get(month_start=month_start)
        analytics_available &= listening["analytics_available"]
        hours = listening["total_listening_hours"]
        metrics.append(
            _metric(
                "Total listening hours this month",
                f"{hours:,.1f}" if hours is not None else "—",
                "headphones",
                _admin_url(
                    "analytics",
                    "dailyplatformmetric",
                    filters={"date__gte": month_start.isoformat()},
                ),
            )
        )

    if permissions["author_analytics"]:
        result = popular_author_service.get(month_start=month_start)
        analytics_available &= result["analytics_available"]
        sections.append(
            _section(
                "popular-authors",
                "Popular authors",
                ("Author", "Plays"),
                [
                    {
                        "url": _admin_url("authors", "author", object_id=item["id"]),
                        "cells": (item["name"], f"{item['plays']:,}"),
                    }
                    for item in result["items"]
                ],
                (
                    "No author analytics are available for this month."
                    if result["analytics_available"]
                    else "Author analytics are temporarily unavailable."
                ),
                _admin_url("analytics", "dailyauthormetric"),
            )
        )

    if permissions["narrator_analytics"]:
        result = popular_narrator_service.get(month_start=month_start)
        analytics_available &= result["analytics_available"]
        sections.append(
            _section(
                "popular-narrators",
                "Popular narrators",
                ("Narrator", "Plays"),
                [
                    {
                        "url": _admin_url(
                            "narrators", "narrator", object_id=item["id"]
                        ),
                        "cells": (item["name"], f"{item['plays']:,}"),
                    }
                    for item in result["items"]
                ],
                (
                    "No narrator analytics are available for this month."
                    if result["analytics_available"]
                    else "Narrator analytics are temporarily unavailable."
                ),
                _admin_url("analytics", "dailynarratormetric"),
            )
        )

    metric_order = {
        label: position
        for position, label in enumerate(
            (
                "Total published tracks",
                "Draft tracks",
                "Tracks processing",
                "Failed processing jobs",
                "Total literary works",
                "Total authors",
                "Total narrators",
                "Total playlists",
                "Registered users",
                "Active premium subscriptions",
                "Pending editorial reviews",
                "Total listening hours this month",
            )
        )
    }
    section_order = {
        identifier: position
        for position, identifier in enumerate(
            (
                "tracks-requiring-attention",
                "recent-uploads",
                "recent-publications",
                "failed-processing",
                "pending-reviews",
                "rights-warnings",
                "recent-users",
                "most-played",
                "popular-authors",
                "popular-narrators",
                "upcoming-publications",
            )
        )
    }
    metrics.sort(key=lambda item: metric_order[item["label"]])
    sections.sort(key=lambda item: section_order[item["identifier"]])
    return {
        "dashboard_metrics": metrics,
        "dashboard_sections": sections,
        "dashboard_generated_at": now,
        "dashboard_analytics_available": analytics_available,
    }
