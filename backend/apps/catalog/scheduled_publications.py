from dataclasses import dataclass
from datetime import datetime
from typing import TypedDict

from django.utils import timezone

from apps.catalog.models import AudioTrack, TrackProcessingStatus, TrackReviewStatus
from apps.catalog.review_workflow import copyright_readiness_issues


class ScheduledPublicationItem(TypedDict):
    id: object
    title: str
    category: str
    author: str
    narrator: str
    scheduled_time: datetime
    processing_ready: bool
    copyright_ready: bool
    copyright_issues: tuple[str, ...]
    publication_status: str
    assigned_editor: str


@dataclass(frozen=True)
class ScheduledPublicationGroup:
    identifier: str
    title: str
    items: list[ScheduledPublicationItem]


class ScheduledPublicationAdminService:
    """Efficient presentation data for future track publications."""

    def get_groups(self, *, now=None):
        now = now or timezone.now()
        local_now = timezone.localtime(now)
        today = local_now.date()
        tracks = (
            AudioTrack.objects.filter(
                review_status=TrackReviewStatus.SCHEDULED,
                is_published=True,
                published_at__gt=now,
            )
            .select_related(
                "work",
                "work__author",
                "work__category",
                "narrator",
                "reviewed_by",
            )
            .prefetch_related("work__copyright_licenses__documents")
            .defer(
                "transcript",
                "waveform_data",
                "description_ne",
                "description_en",
            )
            .order_by("published_at", "title_ne", "id")
        )
        groups = {
            "today": ScheduledPublicationGroup("today", "Today", []),
            "tomorrow": ScheduledPublicationGroup("tomorrow", "Tomorrow", []),
            "week": ScheduledPublicationGroup("week", "This week", []),
            "later": ScheduledPublicationGroup("later", "Later", []),
        }
        for track in tracks:
            local_time = timezone.localtime(track.published_at)
            day_offset = (local_time.date() - today).days
            if day_offset == 0:
                group = groups["today"]
            elif day_offset == 1:
                group = groups["tomorrow"]
            elif day_offset <= 6:
                group = groups["week"]
            else:
                group = groups["later"]
            rights_issues = copyright_readiness_issues(
                track.work,
                on_date=local_time.date(),
            )
            group.items.append(
                {
                    "id": track.pk,
                    "title": track.title_ne,
                    "category": track.work.category.name_ne,
                    "author": track.work.author.name_ne,
                    "narrator": track.narrator.name_ne,
                    "scheduled_time": local_time,
                    "processing_ready": (
                        track.processing_status == TrackProcessingStatus.READY
                    ),
                    "copyright_ready": not rights_issues,
                    "copyright_issues": rights_issues,
                    "publication_status": track.get_review_status_display(),
                    "assigned_editor": (
                        str(track.reviewed_by) if track.reviewed_by else "Unassigned"
                    ),
                }
            )
        return tuple(groups.values())


scheduled_publication_admin_service = ScheduledPublicationAdminService()
