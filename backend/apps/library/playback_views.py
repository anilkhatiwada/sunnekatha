from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import GenericAPIView, ListAPIView
from rest_framework.response import Response

from apps.accounts.permissions import IsAuthenticatedAndActive
from apps.catalog.track_views import public_track_queryset
from apps.library.models import ListeningHistory, PlaybackSession
from apps.library.playback import playback_session_service
from apps.library.serializers import (
    EndPlaybackSessionSerializer,
    ListeningHistorySerializer,
    PlaybackSessionSerializer,
    RecentlyPlayedSerializer,
    StartPlaybackSessionSerializer,
    UpdatePlaybackSessionSerializer,
)


def history_queryset():
    return (
        ListeningHistory.objects.filter(
            track_id__in=public_track_queryset().values("pk")
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
    )


class StartPlaybackSessionView(GenericAPIView):
    permission_classes = [IsAuthenticatedAndActive]
    serializer_class = StartPlaybackSessionSerializer

    @extend_schema(
        responses={200: PlaybackSessionSerializer, 201: PlaybackSessionSerializer}
    )
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        track = get_object_or_404(
            public_track_queryset(),
            pk=serializer.validated_data["trackId"],
        )
        session, created = playback_session_service.start(
            user=request.user,
            track=track,
            device_id=serializer.validated_data["deviceId"],
            position_seconds=serializer.validated_data["positionSeconds"],
            client_event_id=serializer.validated_data.get("clientEventId", ""),
        )
        return Response(
            PlaybackSessionSerializer(session).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class PlaybackSessionView(GenericAPIView):
    permission_classes = [IsAuthenticatedAndActive]
    serializer_class = UpdatePlaybackSessionSerializer

    def get_session(self, session_id):
        return get_object_or_404(
            PlaybackSession.objects.select_related("track"),
            pk=session_id,
            user=self.request.user,
        )

    @extend_schema(responses=PlaybackSessionSerializer)
    def patch(self, request, session_id):
        session = self.get_session(session_id)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        updated = playback_session_service.update(
            session=session,
            listened_seconds=serializer.validated_data["listenedSeconds"],
            event_type=serializer.validated_data.get("eventType"),
            position_seconds=serializer.validated_data.get("positionSeconds"),
            client_event_id=serializer.validated_data.get("clientEventId", ""),
            metadata=serializer.validated_data.get("metadata"),
        )
        return Response(PlaybackSessionSerializer(updated).data)


class EndPlaybackSessionView(GenericAPIView):
    permission_classes = [IsAuthenticatedAndActive]
    serializer_class = EndPlaybackSessionSerializer

    def get_session(self, session_id):
        return get_object_or_404(
            PlaybackSession.objects.select_related("track"),
            pk=session_id,
            user=self.request.user,
        )

    @extend_schema(responses=PlaybackSessionSerializer)
    def post(self, request, session_id):
        session = self.get_session(session_id)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ended, _ = playback_session_service.end(
            session=session,
            listened_seconds=serializer.validated_data.get("listenedSeconds"),
            completed=serializer.validated_data["completed"],
            position_seconds=serializer.validated_data.get("positionSeconds"),
            client_event_id=serializer.validated_data.get("clientEventId", ""),
        )
        return Response(PlaybackSessionSerializer(ended).data)


class ListeningHistoryListView(ListAPIView):
    permission_classes = [IsAuthenticatedAndActive]
    serializer_class = ListeningHistorySerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return ListeningHistory.objects.none()
        return (
            history_queryset()
            .filter(user=self.request.user)
            .order_by(
                "-last_listened_at",
                "id",
            )
        )


class RecentlyPlayedListView(ListAPIView):
    permission_classes = [IsAuthenticatedAndActive]
    serializer_class = RecentlyPlayedSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return ListeningHistory.objects.none()
        return (
            history_queryset()
            .filter(user=self.request.user)
            .order_by(
                "-last_listened_at",
                "id",
            )
        )
