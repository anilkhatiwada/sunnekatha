from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.generics import GenericAPIView, ListAPIView, RetrieveUpdateAPIView
from rest_framework.response import Response

from apps.catalog.models import AudioTrack, TrackProcessingStatus, TrackReviewStatus
from apps.catalog.review_workflow import track_review_workflow
from apps.creators.models import CreatorProfile, RightsLicenseAudit
from apps.creators.permissions import (
    IsCreatorOrStaff,
    can_manage_draft,
    can_manage_rights,
    owned_tracks,
)
from apps.creators.serializers import (
    CreatorAnalyticsSerializer,
    CreatorProfileSerializer,
    CreatorTrackSerializer,
    DraftMetadataSerializer,
    ProcessingStatusSerializer,
)
from apps.uploads.models import UploadSession
from apps.uploads.serializers import UploadSessionSerializer


def creator_track_queryset(user):
    return (
        owned_tracks(user)
        .select_related("work", "work__author", "album", "narrator", "language")
        .prefetch_related("work__genres", "work__moods")
    )


class CreatorProfileView(RetrieveUpdateAPIView):
    permission_classes = [IsCreatorOrStaff]
    serializer_class = CreatorProfileSerializer

    def get_object(self):
        profile, _ = CreatorProfile.objects.get_or_create(
            user=self.request.user,
            defaults={
                "display_name": (
                    self.request.user.display_name or self.request.user.username
                ),
                "roles": [],
                "is_approved": self.request.user.is_staff,
            },
        )
        return profile


class CreatorTrackListView(ListAPIView):
    permission_classes = [IsCreatorOrStaff]
    serializer_class = CreatorTrackSerializer
    queryset = AudioTrack.objects.none()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return self.queryset
        return creator_track_queryset(self.request.user).order_by("-updated_at", "id")


class CreatorDraftTrackListView(CreatorTrackListView):
    def get_queryset(self):
        return super().get_queryset().filter(is_published=False)


class CreatorUploadSessionListView(ListAPIView):
    permission_classes = [IsCreatorOrStaff]
    serializer_class = UploadSessionSerializer
    queryset = UploadSession.objects.none()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return self.queryset
        return UploadSession.objects.filter(user=self.request.user)


class OwnedTrackMixin:
    permission_classes = [IsCreatorOrStaff]

    def get_track(self):
        return get_object_or_404(
            creator_track_queryset(self.request.user),
            slug=self.kwargs["slug"],
        )


class CreatorProcessingStatusView(OwnedTrackMixin, GenericAPIView):
    serializer_class = ProcessingStatusSerializer

    def get(self, request, slug):
        del request, slug
        return Response(self.get_serializer(self.get_track()).data)


class SubmitTrackReviewView(OwnedTrackMixin, GenericAPIView):
    serializer_class = ProcessingStatusSerializer

    def post(self, request, slug):
        del slug
        track = self.get_track()
        if not can_manage_draft(self.request.user, track):
            raise PermissionDenied("Only owned drafts can be submitted.")
        try:
            track_review_workflow.transition(
                track_id=track.pk,
                target=TrackReviewStatus.SUBMITTED,
                actor=request.user,
            )
        except DjangoValidationError as exc:
            raise ValidationError({"reviewStatus": exc.messages[0]}) from exc
        track.refresh_from_db()
        return Response(self.get_serializer(track).data)


class UpdateDraftMetadataView(OwnedTrackMixin, GenericAPIView):
    serializer_class = DraftMetadataSerializer

    def patch(self, request, slug):
        del slug
        track = self.get_track()
        if not can_manage_draft(request.user, track):
            raise PermissionDenied("Only owned drafts can be edited.")
        rights_keys = {"copyrightStatus", "copyrightOwner", "licenseNotes"}
        requested_rights = rights_keys.intersection(request.data)
        if requested_rights and not can_manage_rights(request.user, track):
            raise PermissionDenied("Rights-holder access is required.")
        serializer = self.get_serializer(
            track,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        rights = serializer.context.get("rights_changes", {})
        if rights:
            field_map = {
                "copyrightStatus": "copyright_status",
                "copyrightOwner": "copyright_owner",
                "licenseNotes": "license_notes",
            }
            changes = {}
            for api_field, value in rights.items():
                model_field = field_map[api_field]
                old = getattr(track.work, model_field)
                if old != value:
                    changes[api_field] = {"from": old, "to": value}
                    setattr(track.work, model_field, value)
            if changes:
                track.work.save(
                    update_fields=(
                        *(field_map[key] for key in changes),
                        "updated_at",
                    )
                )
                RightsLicenseAudit.objects.create(
                    track=track,
                    actor=request.user,
                    changes=changes,
                )
        return Response(CreatorTrackSerializer(track).data)


class ApprovePublishTrackView(OwnedTrackMixin, GenericAPIView):
    serializer_class = CreatorTrackSerializer

    def post(self, request, slug):
        del slug
        if not (
            request.user.has_perm("catalog.approve_audiotrack")
            and request.user.has_perm("catalog.publish_audiotrack")
        ):
            raise PermissionDenied("Editor approval and publisher access are required.")
        track = self.get_track()
        if track.review_status != TrackReviewStatus.SUBMITTED:
            raise ValidationError({"reviewStatus": "Track is not submitted."})
        if track.processing_status != TrackProcessingStatus.READY:
            raise ValidationError({"processingStatus": "Track is not ready."})
        track_review_workflow.transition(
            track_id=track.pk,
            target=TrackReviewStatus.APPROVED,
            actor=request.user,
        )
        track_review_workflow.transition(
            track_id=track.pk,
            target=TrackReviewStatus.PUBLISHED,
            actor=request.user,
        )
        track.refresh_from_db()
        return Response(self.get_serializer(track).data)


class CreatorTrackAnalyticsView(OwnedTrackMixin, GenericAPIView):
    serializer_class = CreatorAnalyticsSerializer

    def get(self, request, slug):
        del request, slug
        track = self.get_track()
        playback = track.playback_sessions.aggregate(
            playbackSessions=Count("id"),
            completedSessions=Count("id", filter=Q(completed=True)),
            listenedSeconds=Sum("listened_seconds"),
        )
        playback["listenedSeconds"] = playback["listenedSeconds"] or 0
        payload = {
            "playCount": track.play_count_cache,
            "favoriteCount": track.favorited_by.count(),
            "uniqueListeners": track.listening_progress.values("user_id")
            .distinct()
            .count(),
            **playback,
        }
        return Response(self.get_serializer(payload).data)
