from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import status
from rest_framework.generics import GenericAPIView, ListAPIView
from rest_framework.response import Response

from apps.accounts.permissions import IsAuthenticatedAndActive
from apps.catalog.models import AudioTrack
from apps.catalog.track_views import public_track_queryset
from apps.common.schema import with_standard_errors
from apps.library.models import ListeningProgress
from apps.library.progress import listening_progress_service
from apps.library.serializers import (
    ContinueListeningSerializer,
    ListeningProgressSerializer,
    ListeningProgressUpdateSerializer,
)


class ListeningProgressDetailView(GenericAPIView):
    permission_classes = [IsAuthenticatedAndActive]
    serializer_class = ListeningProgressUpdateSerializer

    def get_track(self, track_id):
        return get_object_or_404(
            AudioTrack.objects.published().only("id", "duration_seconds"),
            pk=track_id,
        )

    def get_progress(self, track_id):
        return get_object_or_404(
            ListeningProgress.objects.all(),
            user=self.request.user,
            track_id=track_id,
        )

    @extend_schema(
        summary="Get progress for one track",
        responses=with_standard_errors({200: ListeningProgressSerializer}),
        tags=["me"],
    )
    def get(self, request, track_id):
        progress = self.get_progress(track_id)
        return Response(ListeningProgressSerializer(progress).data)

    def update(self, request, track_id):
        track = self.get_track(track_id)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        progress = listening_progress_service.update(
            user=request.user,
            track=track,
            position_seconds=serializer.validated_data["progressSeconds"],
            duration_seconds=serializer.validated_data["durationSeconds"],
        )
        return Response(ListeningProgressSerializer(progress).data)

    @extend_schema(
        summary="Replace listening progress",
        description=(
            "Idempotently upserts one progress row for this user and track. "
            "Positions use seconds; progress at 90% or above is completed."
        ),
        request=ListeningProgressUpdateSerializer,
        responses=with_standard_errors({200: ListeningProgressSerializer}),
        examples=[
            OpenApiExample(
                "Periodic progress update",
                value={"progressSeconds": 315.25, "durationSeconds": 842},
                request_only=True,
            ),
            OpenApiExample(
                "Stored progress",
                value={
                    "trackId": "f60f09ad-7bc5-4cf0-8368-b199aa076d59",
                    "progressSeconds": 315.25,
                    "durationSeconds": 842,
                    "progressPercentage": 37.44,
                    "isCompleted": False,
                    "lastListenedAt": "2026-07-23T17:00:00Z",
                    "updatedAt": "2026-07-23T17:00:00Z",
                },
                response_only=True,
            ),
        ],
        tags=["me"],
    )
    def put(self, request, track_id):
        return self.update(request, track_id)

    @extend_schema(
        summary="Partially update listening progress",
        description=(
            "Uses the same complete payload and idempotent semantics as PUT. "
            "Send every 15–30 seconds and on pause, track change, or page exit."
        ),
        request=ListeningProgressUpdateSerializer,
        responses=with_standard_errors({200: ListeningProgressSerializer}),
        tags=["me"],
    )
    def patch(self, request, track_id):
        return self.update(request, track_id)

    @extend_schema(
        summary="Delete progress for one track",
        request=None,
        responses=with_standard_errors({204: None}),
        tags=["me"],
    )
    def delete(self, request, track_id):
        ListeningProgress.objects.filter(
            user=request.user,
            track_id=track_id,
        ).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MarkListeningCompletedView(GenericAPIView):
    permission_classes = [IsAuthenticatedAndActive]
    serializer_class = ListeningProgressSerializer

    @extend_schema(
        summary="Mark a track completed",
        request=None,
        responses=with_standard_errors({200: ListeningProgressSerializer}),
        tags=["me"],
    )
    def post(self, request, track_id):
        track = get_object_or_404(
            AudioTrack.objects.published().only("id", "duration_seconds"),
            pk=track_id,
        )
        progress = listening_progress_service.mark_completed(
            user=request.user,
            track=track,
        )
        return Response(ListeningProgressSerializer(progress).data)


class RemoveContinueListeningView(GenericAPIView):
    permission_classes = [IsAuthenticatedAndActive]
    serializer_class = ListeningProgressSerializer

    @extend_schema(
        summary="Remove a track from continue listening",
        request=None,
        responses=with_standard_errors({204: None}),
        tags=["me"],
    )
    def delete(self, request, track_id):
        ListeningProgress.objects.filter(
            user=request.user,
            track_id=track_id,
        ).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ContinueListeningView(ListAPIView):
    permission_classes = [IsAuthenticatedAndActive]
    serializer_class = ContinueListeningSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return ListeningProgress.objects.none()
        return (
            ListeningProgress.objects.filter(
                user=self.request.user,
                is_completed=False,
                position_seconds__gt=0,
                track_id__in=public_track_queryset().values("pk"),
            )
            .select_related(
                "track",
                "track__work",
                "track__work__author",
                "track__work__category",
                "track__album",
                "track__narrator",
                "track__language",
            )
            .prefetch_related("track__work__genres", "track__work__moods")
            .order_by("-last_listened_at", "-updated_at", "id")
        )
