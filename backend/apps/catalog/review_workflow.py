from dataclasses import dataclass
from datetime import datetime

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from apps.catalog.models import (
    AudioTrack,
    CopyrightStatus,
    RightsVerificationStatus,
    TrackProcessingStatus,
    TrackReviewEvent,
    TrackReviewStatus,
)
from apps.catalog.services import EditorialResult, EditorialService
from apps.common.admin_actions import (
    BulkActionFailure,
    BulkActionReport,
    validation_message,
)
from apps.common.audit import administrative_audit_service
from apps.common.models import AdministrativeAuditAction
from apps.notifications.services import notification_service


@dataclass(frozen=True)
class ReviewTransition:
    target: str
    allowed_from: frozenset[str]
    permission: str | None = None
    reason_required: bool = False


TRANSITIONS = {
    TrackReviewStatus.SUBMITTED: ReviewTransition(
        TrackReviewStatus.SUBMITTED,
        frozenset(
            {
                TrackReviewStatus.DRAFT,
                TrackReviewStatus.CHANGES_REQUESTED,
                TrackReviewStatus.REJECTED,
            }
        ),
    ),
    TrackReviewStatus.CHANGES_REQUESTED: ReviewTransition(
        TrackReviewStatus.CHANGES_REQUESTED,
        frozenset({TrackReviewStatus.SUBMITTED}),
        permission="catalog.approve_audiotrack",
        reason_required=True,
    ),
    TrackReviewStatus.APPROVED: ReviewTransition(
        TrackReviewStatus.APPROVED,
        frozenset({TrackReviewStatus.SUBMITTED}),
        permission="catalog.approve_audiotrack",
    ),
    TrackReviewStatus.REJECTED: ReviewTransition(
        TrackReviewStatus.REJECTED,
        frozenset({TrackReviewStatus.SUBMITTED}),
        permission="catalog.approve_audiotrack",
        reason_required=True,
    ),
    TrackReviewStatus.SCHEDULED: ReviewTransition(
        TrackReviewStatus.SCHEDULED,
        frozenset({TrackReviewStatus.APPROVED}),
        permission="catalog.publish_audiotrack",
    ),
    TrackReviewStatus.PUBLISHED: ReviewTransition(
        TrackReviewStatus.PUBLISHED,
        frozenset({TrackReviewStatus.APPROVED, TrackReviewStatus.SCHEDULED}),
        permission="catalog.publish_audiotrack",
    ),
    TrackReviewStatus.ARCHIVED: ReviewTransition(
        TrackReviewStatus.ARCHIVED,
        frozenset(
            {
                TrackReviewStatus.DRAFT,
                TrackReviewStatus.CHANGES_REQUESTED,
                TrackReviewStatus.APPROVED,
                TrackReviewStatus.SCHEDULED,
                TrackReviewStatus.PUBLISHED,
                TrackReviewStatus.REJECTED,
            }
        ),
        permission="catalog.publish_audiotrack",
    ),
}


class TrackReviewWorkflow:
    """Permission-aware, audited state transitions for editorial tracks."""

    def transition_many(
        self,
        *,
        queryset,
        target: str,
        actor,
        comment: str = "",
        scheduled_for: datetime | None = None,
    ) -> EditorialResult:
        total = queryset.count()
        updated = 0
        for track_id in queryset.values_list("pk", flat=True):
            try:
                self.transition(
                    track_id=track_id,
                    target=target,
                    actor=actor,
                    comment=comment,
                    scheduled_for=scheduled_for,
                )
            except (PermissionDenied, ValidationError):
                continue
            updated += 1
        return EditorialResult(updated=updated, skipped=total - updated)

    def transition_many_detailed(
        self,
        *,
        queryset,
        target: str,
        actor,
        comment: str = "",
        scheduled_for: datetime | None = None,
    ) -> BulkActionReport:
        """Apply bulk transitions without concealing invalid or unauthorized rows."""
        report = BulkActionReport()
        for track_id, label in queryset.values_list("pk", "title_ne"):
            try:
                self.transition(
                    track_id=track_id,
                    target=target,
                    actor=actor,
                    comment=comment,
                    scheduled_for=scheduled_for,
                )
            except (PermissionDenied, ValidationError) as exc:
                report.failures.append(
                    BulkActionFailure(str(track_id), label, validation_message(exc))
                )
            else:
                report.succeeded += 1
        return report

    @transaction.atomic
    def transition(
        self,
        *,
        track_id,
        target: str,
        actor,
        comment: str = "",
        scheduled_for: datetime | None = None,
    ) -> AudioTrack:
        transition = TRANSITIONS.get(target)
        if transition is None:
            raise ValidationError("Unsupported editorial review transition.")
        track = (
            AudioTrack.objects.select_for_update()
            # Keep nullable relationships out of the locking join. PostgreSQL
            # rejects FOR UPDATE when it targets the nullable side of an outer
            # join; narrator.user is loaded separately only when authorization
            # needs it.
            .select_related("work")
            .prefetch_related(
                "contributors__creator",
                "work__copyright_licenses__documents",
            )
            .get(pk=track_id)
        )
        self._authorize(track, transition=transition, actor=actor)
        comment = comment.strip()
        if transition.reason_required and not comment:
            raise ValidationError("A reason is required for this transition.")
        if track.review_status not in transition.allowed_from:
            raise ValidationError(
                f"Cannot move from {track.get_review_status_display()} "
                f"to {TrackReviewStatus(target).label}."
            )
        if (
            target
            in {
                TrackReviewStatus.SUBMITTED,
                TrackReviewStatus.APPROVED,
                TrackReviewStatus.SCHEDULED,
                TrackReviewStatus.PUBLISHED,
            }
            and track.processing_status != TrackProcessingStatus.READY
        ):
            raise ValidationError("Audio processing must be ready.")
        if target == TrackReviewStatus.SCHEDULED:
            if scheduled_for is None or timezone.is_naive(scheduled_for):
                raise ValidationError(
                    "Scheduled publication time must be timezone-aware."
                )
            if scheduled_for <= timezone.now():
                raise ValidationError("Scheduled publication must be in the future.")
        if target in {
            TrackReviewStatus.SCHEDULED,
            TrackReviewStatus.PUBLISHED,
        }:
            rights_issues = copyright_readiness_issues(
                track.work,
                on_date=(
                    timezone.localtime(scheduled_for).date()
                    if scheduled_for
                    else timezone.localdate()
                ),
            )
            if rights_issues:
                raise ValidationError("; ".join(rights_issues))

        previous = track.review_status
        previous_is_published = track.is_published
        previous_published_at = track.published_at
        now = timezone.now()
        track.review_status = target
        track.review_comments = comment
        update_fields = ["review_status", "review_comments", "updated_at"]
        if target == TrackReviewStatus.SUBMITTED:
            track.submitted_at = now
            track.reviewed_at = None
            track.reviewed_by = None
            update_fields.extend(("submitted_at", "reviewed_at", "reviewed_by"))
        elif target in {
            TrackReviewStatus.CHANGES_REQUESTED,
            TrackReviewStatus.APPROVED,
            TrackReviewStatus.REJECTED,
        }:
            track.reviewed_at = now
            track.reviewed_by = actor
            update_fields.extend(("reviewed_at", "reviewed_by"))
        elif target == TrackReviewStatus.SCHEDULED:
            track.is_published = True
            track.published_at = scheduled_for
            update_fields.extend(("is_published", "published_at"))
        elif target == TrackReviewStatus.PUBLISHED:
            # Delegate media/publication side effects to the established service.
            track.review_status = TrackReviewStatus.APPROVED
            track.save(update_fields=("review_status", "updated_at"))
            if track.is_published:
                EditorialService.unpublish_tracks(
                    AudioTrack.objects.filter(pk=track.pk),
                    actor=actor,
                )
            result = EditorialService.publish_tracks(
                AudioTrack.objects.filter(pk=track.pk),
                actor=actor,
            )
            if result.updated != 1:
                raise ValidationError("Track could not be published.")
            track.refresh_from_db(fields=("is_published", "published_at"))
            track.review_status = TrackReviewStatus.PUBLISHED
            update_fields = ["review_status", "review_comments", "updated_at"]
        elif target == TrackReviewStatus.ARCHIVED:
            track.is_published = False
            track.published_at = None
            update_fields.extend(("is_published", "published_at"))

        track.save(update_fields=update_fields)
        TrackReviewEvent.objects.create(
            track=track,
            from_status=previous,
            to_status=target,
            actor=actor,
            comment=comment,
            scheduled_for=scheduled_for,
        )
        if target == TrackReviewStatus.APPROVED:
            notification_service.creator_submission_approved(track)
        elif target in {
            TrackReviewStatus.CHANGES_REQUESTED,
            TrackReviewStatus.REJECTED,
        }:
            notification_service.creator_submission_reviewed(
                track,
                status=target,
                comment=comment,
            )
        audit_actions = {
            TrackReviewStatus.SUBMITTED: AdministrativeAuditAction.REVIEW_SUBMITTED,
            TrackReviewStatus.APPROVED: AdministrativeAuditAction.APPROVED,
            TrackReviewStatus.REJECTED: AdministrativeAuditAction.REJECTED,
            TrackReviewStatus.PUBLISHED: AdministrativeAuditAction.PUBLISHED,
            TrackReviewStatus.ARCHIVED: AdministrativeAuditAction.UNPUBLISHED,
        }
        if action := audit_actions.get(target):
            administrative_audit_service.record(
                actor=actor,
                action=action,
                obj=track,
                reason=comment,
                before={
                    "review_status": previous,
                    "is_published": previous_is_published,
                    "published_at": previous_published_at,
                },
                after={
                    "review_status": track.review_status,
                    "is_published": track.is_published,
                    "published_at": track.published_at,
                },
            )
        return track

    @transaction.atomic
    def reschedule(self, *, track_id, scheduled_for, actor, comment=""):
        if not actor.has_perm("catalog.publish_audiotrack"):
            raise PermissionDenied("Publishing permission is required.")
        if scheduled_for is None or timezone.is_naive(scheduled_for):
            raise ValidationError("Scheduled publication time must be timezone-aware.")
        if scheduled_for <= timezone.now():
            raise ValidationError("Scheduled publication must be in the future.")
        track = (
            AudioTrack.objects.select_for_update()
            .select_related("work")
            .prefetch_related("work__copyright_licenses__documents")
            .get(pk=track_id)
        )
        if track.review_status != TrackReviewStatus.SCHEDULED:
            raise ValidationError("Only scheduled content can be rescheduled.")
        if track.processing_status != TrackProcessingStatus.READY:
            raise ValidationError("Audio processing must be ready.")
        issues = copyright_readiness_issues(
            track.work,
            on_date=timezone.localtime(scheduled_for).date(),
        )
        if issues:
            raise ValidationError("; ".join(issues))
        previous_time = track.published_at
        track.published_at = scheduled_for
        track.save(update_fields=("published_at", "updated_at"))
        TrackReviewEvent.objects.create(
            track=track,
            from_status=TrackReviewStatus.SCHEDULED,
            to_status=TrackReviewStatus.SCHEDULED,
            actor=actor,
            comment=comment or f"Rescheduled from {previous_time.isoformat()}.",
            scheduled_for=scheduled_for,
        )
        return track

    @transaction.atomic
    def cancel_schedule(self, *, track_id, actor, comment=""):
        if not actor.has_perm("catalog.publish_audiotrack"):
            raise PermissionDenied("Publishing permission is required.")
        track = AudioTrack.objects.select_for_update().get(pk=track_id)
        if track.review_status != TrackReviewStatus.SCHEDULED:
            raise ValidationError("Only scheduled content can be canceled.")
        previous_time = track.published_at
        EditorialService.unpublish_tracks(
            AudioTrack.objects.filter(pk=track.pk),
            actor=actor,
        )
        track.refresh_from_db(fields=("is_published", "published_at"))
        track.review_status = TrackReviewStatus.APPROVED
        track.save(update_fields=("review_status", "updated_at"))
        TrackReviewEvent.objects.create(
            track=track,
            from_status=TrackReviewStatus.SCHEDULED,
            to_status=TrackReviewStatus.APPROVED,
            actor=actor,
            comment=comment or "Scheduled publication canceled.",
            scheduled_for=previous_time,
        )
        administrative_audit_service.record(
            actor=actor,
            action=AdministrativeAuditAction.UNPUBLISHED,
            obj=track,
            reason=comment or "Scheduled publication canceled.",
            before={
                "review_status": TrackReviewStatus.SCHEDULED,
                "is_published": True,
                "published_at": previous_time,
            },
            after={
                "review_status": TrackReviewStatus.APPROVED,
                "is_published": False,
            },
        )
        return track

    @staticmethod
    def _authorize(track, *, transition: ReviewTransition, actor):
        if not actor or not actor.is_authenticated or not actor.is_active:
            raise PermissionDenied("Authentication is required.")
        if transition.permission and not actor.has_perm(transition.permission):
            raise PermissionDenied("You do not have permission for this transition.")
        if transition.target == TrackReviewStatus.SUBMITTED:
            owns_track = (
                track.narrator.user_id == actor.pk
                or track.contributors.filter(creator__user=actor).exists()
            )
            if not (owns_track or actor.has_perm("catalog.change_audiotrack")):
                raise PermissionDenied(
                    "Only a creator or editor can submit this track."
                )
        if transition.target == TrackReviewStatus.APPROVED:
            owns_track = (
                track.narrator.user_id == actor.pk
                or track.contributors.filter(creator__user=actor).exists()
            )
            if owns_track and not actor.has_perm("catalog.approve_own_audiotrack"):
                raise PermissionDenied("Creators cannot approve their own submissions.")


track_review_workflow = TrackReviewWorkflow()


def copyright_readiness_issues(work, *, on_date=None) -> tuple[str, ...]:
    """Return stored-rights workflow blockers without making legal conclusions."""
    on_date = on_date or timezone.localdate()
    if work.copyright_status == CopyrightStatus.PUBLIC_DOMAIN:
        return ()
    if work.copyright_status in {
        CopyrightStatus.UNKNOWN,
        CopyrightStatus.PERMISSION_PENDING,
        CopyrightStatus.PERMISSION_EXPIRED,
        CopyrightStatus.PERMISSION_REJECTED,
        CopyrightStatus.OWNERSHIP_UNCLEAR,
    }:
        return ("Copyright status is unresolved",)
    issues = []
    if not work.copyright_owner.strip():
        issues.append("Copyright owner is missing")
    licenses = work.copyright_licenses.all()
    valid_license = any(
        license.allows_audio
        and license.verification_status == RightsVerificationStatus.VERIFIED
        and (license.effective_date is None or license.effective_date <= on_date)
        and (license.expiration_date is None or license.expiration_date >= on_date)
        and any(document.is_verified for document in license.documents.all())
        for license in licenses
    )
    if not valid_license:
        issues.append(
            "A verified, effective audio permission and document are required"
        )
    return tuple(issues)


def review_readiness_issues(track) -> tuple[str, ...]:
    """Return editor-facing reasons a submitted track cannot be safely approved."""
    issues = []
    work = track.work
    if track.processing_status != TrackProcessingStatus.READY:
        issues.append("Audio processing is not ready")
    if work.copyright_status == CopyrightStatus.UNKNOWN:
        issues.append("Copyright status is unknown")
    if (
        work.copyright_status
        in {
            CopyrightStatus.COPYRIGHTED,
            CopyrightStatus.LICENSED,
            CopyrightStatus.PERMISSION_GRANTED,
        }
        and not work.copyright_owner.strip()
    ):
        issues.append("Copyright owner is missing")
    if not work.cover_image:
        issues.append("Cover image is missing")
    if not track.narrator_id:
        issues.append("Narrator is missing")
    if not track.title_ne.strip() or not work_id_metadata_complete(track):
        issues.append("Required metadata is incomplete")
    return tuple(issues)


def work_id_metadata_complete(track) -> bool:
    return bool(
        track.work_id
        and track.language_id
        and track.work.author_id
        and track.work.content_type
    )


class PendingReviewService:
    @transaction.atomic
    def assign_reviewer(self, *, queryset, reviewer, actor) -> EditorialResult:
        if not actor.has_perm("catalog.approve_audiotrack"):
            raise PermissionDenied("Editor permission is required.")
        if not reviewer.has_perm("catalog.approve_audiotrack"):
            raise ValidationError("The assigned reviewer must be an editor.")
        tracks = list(
            AudioTrack.objects.select_for_update().filter(
                pk__in=queryset,
                review_status=TrackReviewStatus.SUBMITTED,
            )
        )
        for track in tracks:
            previous_reviewer = track.reviewed_by
            track.reviewed_by = reviewer
            track.save(update_fields=("reviewed_by", "updated_at"))
            TrackReviewEvent.objects.create(
                track=track,
                from_status=track.review_status,
                to_status=track.review_status,
                actor=actor,
                comment=(
                    f"Reviewer assigned to {reviewer}. "
                    f"Previous reviewer: {previous_reviewer or 'unassigned'}."
                ),
            )
        return EditorialResult(
            updated=len(tracks),
            skipped=queryset.count() - len(tracks),
        )

    def assign_reviewer_detailed(
        self, *, queryset, reviewer, actor
    ) -> BulkActionReport:
        if not actor.has_perm("catalog.approve_audiotrack"):
            raise PermissionDenied("Editor permission is required.")
        if not reviewer.has_perm("catalog.approve_audiotrack"):
            raise ValidationError("The assigned reviewer must be an editor.")
        report = BulkActionReport()
        for track_id, label, status in queryset.values_list(
            "pk", "title_ne", "review_status"
        ):
            if status != TrackReviewStatus.SUBMITTED:
                report.failures.append(
                    BulkActionFailure(
                        str(track_id),
                        label,
                        "Only submitted tracks can be assigned.",
                    )
                )
                continue
            result = self.assign_reviewer(
                queryset=queryset.model._base_manager.filter(pk=track_id),
                reviewer=reviewer,
                actor=actor,
            )
            if result.updated:
                report.succeeded += 1
            else:
                report.failures.append(
                    BulkActionFailure(
                        str(track_id),
                        label,
                        "Track changed before the assignment could be saved.",
                    )
                )
        return report

    def approve_safe(self, *, queryset, actor) -> EditorialResult:
        total = queryset.count()
        updated = 0
        tracks = (
            queryset.select_related("work__author", "language", "narrator")
            .filter(review_status=TrackReviewStatus.SUBMITTED)
            .iterator()
        )
        for track in tracks:
            if review_readiness_issues(track):
                continue
            try:
                track_review_workflow.transition(
                    track_id=track.pk,
                    target=TrackReviewStatus.APPROVED,
                    actor=actor,
                )
            except (PermissionDenied, ValidationError):
                continue
            updated += 1
        return EditorialResult(updated=updated, skipped=total - updated)


pending_review_service = PendingReviewService()
