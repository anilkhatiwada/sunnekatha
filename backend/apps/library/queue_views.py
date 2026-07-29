from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from apps.accounts.permissions import IsAuthenticatedAndActive
from apps.catalog.models import AudioTrack
from apps.catalog.track_views import public_track_queryset
from apps.common.schema import with_standard_errors
from apps.library.models import UserQueue, UserQueueItem
from apps.library.queue import user_queue_service
from apps.library.serializers import (
    QueuePositionSerializer,
    QueueRepeatSerializer,
    QueueShuffleSerializer,
    QueueTrackSerializer,
    ReorderQueueSerializer,
    ReplaceQueueSerializer,
    UserQueueSerializer,
)


def queue_queryset():
    return UserQueue.objects.prefetch_related(
        Prefetch(
            "items",
            queryset=UserQueueItem.objects.select_related(
                "track",
                "track__work",
                "track__work__author",
                "track__album",
                "track__narrator",
                "track__language",
            )
            .prefetch_related("track__work__genres", "track__work__moods")
            .order_by("position", "created_at", "id"),
        )
    )


class QueueBaseView(GenericAPIView):
    permission_classes = [IsAuthenticatedAndActive]

    def get_queue(self):
        return user_queue_service.get_or_create(self.request.user)

    def output(self, queue):
        hydrated = queue_queryset().get(pk=queue.pk)
        return Response(
            UserQueueSerializer(hydrated, context={"request": self.request}).data
        )

    @staticmethod
    def get_track(track_id):
        return get_object_or_404(public_track_queryset(), pk=track_id)


class CurrentQueueView(QueueBaseView):
    serializer_class = ReplaceQueueSerializer

    @extend_schema(
        summary="Get the current synchronized queue",
        description=(
            "Returns the authenticated user's server snapshot. The frontend player "
            "remains the immediate source of truth during playback."
        ),
        responses=with_standard_errors({200: UserQueueSerializer}),
        tags=["me"],
    )
    def get(self, request):
        del request
        return self.output(self.get_queue())

    @extend_schema(
        summary="Replace the synchronized queue",
        description=(
            "Transactionally replaces ordered queue items and restoration state. "
            "Duplicate track IDs are allowed and retain distinct queue-item IDs."
        ),
        request=ReplaceQueueSerializer,
        responses=with_standard_errors({200: UserQueueSerializer}),
        examples=[
            OpenApiExample(
                "Replace queue",
                value={
                    "trackIds": [
                        "f60f09ad-7bc5-4cf0-8368-b199aa076d59",
                        "20c1641a-585a-4a71-8b66-1996e702f41b",
                    ],
                    "currentIndex": 0,
                    "positionSeconds": 315.25,
                },
                request_only=True,
            )
        ],
        tags=["me"],
    )
    def put(self, request):
        queue = self.get_queue()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        track_ids = serializer.validated_data["trackIds"]
        tracks = {
            track.id: track
            for track in public_track_queryset().filter(id__in=set(track_ids))
        }
        missing = set(track_ids) - tracks.keys()
        if missing:
            get_object_or_404(AudioTrack.objects.none(), pk=next(iter(missing)))
        ordered_tracks = [tracks[track_id] for track_id in track_ids]
        updated = user_queue_service.replace(
            queue=queue,
            tracks=ordered_tracks,
            current_index=serializer.validated_data["currentIndex"],
            position_seconds=serializer.validated_data["positionSeconds"],
        )
        return self.output(updated)

    @extend_schema(
        summary="Clear the synchronized queue",
        request=None,
        responses=with_standard_errors({204: None}),
        tags=["me"],
    )
    def delete(self, request):
        queue = self.get_queue()
        user_queue_service.clear(queue=queue)
        return Response(status=status.HTTP_204_NO_CONTENT)


class AddQueueTrackView(QueueBaseView):
    serializer_class = QueueTrackSerializer

    @extend_schema(
        summary="Append a track to the queue",
        request=QueueTrackSerializer,
        responses=with_standard_errors({200: UserQueueSerializer}),
        tags=["me"],
    )
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        queue = self.get_queue()
        user_queue_service.add(
            queue=queue,
            track=self.get_track(serializer.validated_data["trackId"]),
        )
        return self.output(queue)


class PlayNextView(QueueBaseView):
    serializer_class = QueueTrackSerializer

    @extend_schema(
        summary="Insert a track after the current item",
        request=QueueTrackSerializer,
        responses=with_standard_errors({200: UserQueueSerializer}),
        tags=["me"],
    )
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        queue = self.get_queue()
        user_queue_service.play_next(
            queue=queue,
            track=self.get_track(serializer.validated_data["trackId"]),
        )
        return self.output(queue)


class RemoveQueueItemView(QueueBaseView):
    serializer_class = UserQueueSerializer

    @extend_schema(request=None, responses={204: None})
    def delete(self, request, item_id):
        queue = self.get_queue()
        user_queue_service.remove(queue=queue, item_id=item_id)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ReorderQueueView(QueueBaseView):
    serializer_class = ReorderQueueSerializer

    @extend_schema(
        summary="Reorder queue items",
        description=(
            "Send every current queue item ID exactly once in the desired order. "
            "The change is transactional and preserves stable item identity."
        ),
        request=ReorderQueueSerializer,
        responses=with_standard_errors({200: UserQueueSerializer}),
        examples=[
            OpenApiExample(
                "Reorder queue",
                value={
                    "itemIds": [
                        "e24195ab-273e-47c2-8d3c-3e91c3664344",
                        "05458955-e05b-43e3-bc09-20128eb034c0",
                    ]
                },
                request_only=True,
            )
        ],
        tags=["me"],
    )
    def patch(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        queue = self.get_queue()
        updated = user_queue_service.reorder(
            queue=queue,
            item_ids=serializer.validated_data["itemIds"],
        )
        return self.output(updated)


class QueuePositionView(QueueBaseView):
    serializer_class = QueuePositionSerializer

    @extend_schema(
        summary="Update queue restoration position",
        description=(
            "Stores the current queue index and playback position for cross-device "
            "restoration. This is not a per-second playback event."
        ),
        request=QueuePositionSerializer,
        responses=with_standard_errors({200: UserQueueSerializer}),
        examples=[
            OpenApiExample(
                "Save queue position",
                value={"currentIndex": 1, "positionSeconds": 42.5},
                request_only=True,
            )
        ],
        tags=["me"],
    )
    def patch(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        queue = self.get_queue()
        updated = user_queue_service.update_position(
            queue=queue,
            current_index=serializer.validated_data["currentIndex"],
            position_seconds=serializer.validated_data["positionSeconds"],
        )
        return self.output(updated)


class QueueShuffleView(QueueBaseView):
    serializer_class = QueueShuffleSerializer

    @extend_schema(responses=UserQueueSerializer)
    def patch(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        queue = self.get_queue()
        queue.is_shuffle_enabled = serializer.validated_data["isShuffleEnabled"]
        queue.save(update_fields=("is_shuffle_enabled", "updated_at"))
        return self.output(queue)


class QueueRepeatView(QueueBaseView):
    serializer_class = QueueRepeatSerializer

    @extend_schema(responses=UserQueueSerializer)
    def patch(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        queue = self.get_queue()
        queue.repeat_mode = serializer.validated_data["repeatMode"]
        queue.save(update_fields=("repeat_mode", "updated_at"))
        return self.output(queue)
