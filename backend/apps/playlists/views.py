from django.conf import settings
from django.db.models import Count, IntegerField, OuterRef, Prefetch, Q, Subquery, Sum
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import NotAuthenticated
from rest_framework.generics import (
    GenericAPIView,
    ListCreateAPIView,
    RetrieveUpdateDestroyAPIView,
)
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from apps.catalog.models import AudioTrack, TrackProcessingStatus
from apps.catalog.views import literary_work_queryset
from apps.common.cache_views import PublicDetailCacheMixin, PublicListCacheMixin
from apps.notifications.services import notification_service
from apps.playlists.models import (
    Playlist,
    PlaylistItem,
    PlaylistType,
    PlaylistVisibility,
)
from apps.playlists.permissions import CanManagePlaylist
from apps.playlists.serializers import (
    AddTrackSerializer,
    AddWorkSerializer,
    CompactPlaylistSerializer,
    DuplicatePlaylistSerializer,
    PlaylistDetailSerializer,
    PlaylistWriteSerializer,
    RemoveTrackSerializer,
    RemoveWorkSerializer,
    ReorderTracksSerializer,
    VisibilitySerializer,
)
from apps.playlists.services import playlist_item_service


def playlist_queryset(*, include_tracks=True):
    playable_items = (
        PlaylistItem.objects.filter(
            Q(
                track__is_published=True,
                track__processing_status=TrackProcessingStatus.READY,
                track__published_at__lte=timezone.now(),
            )
            & (Q(track__stream_file_low__gt="") | Q(track__stream_file_high__gt=""))
            | Q(work__in=literary_work_queryset().discoverable())
        )
        .select_related(
            "track__work__author",
            "track__work__category",
            "track__album",
            "track__narrator",
            "track__language",
            "work__author",
            "work__category",
            "work__language",
        )
        .prefetch_related(
            "track__work__genres",
            "track__work__moods",
            "work__genres",
            "work__moods",
            "work__categories",
            "work__tags",
            Prefetch(
                "work__audio_tracks",
                queryset=AudioTrack.objects.published()
                .filter(Q(stream_file_low__gt="") | Q(stream_file_high__gt=""))
                .select_related(
                    "work",
                    "work__category",
                    "work__author",
                    "album",
                    "narrator",
                    "language",
                )
                .prefetch_related("work__genres", "work__moods", "work__tags")
                .order_by("chapter_number", "track_number", "published_at", "id"),
                to_attr="public_chapters",
            ),
        )
        .order_by("position", "created_at", "id")
    )
    direct_metrics = (
        PlaylistItem.objects.filter(
            playlist=OuterRef("pk"),
            track__is_published=True,
            track__processing_status=TrackProcessingStatus.READY,
            track__published_at__lte=timezone.now(),
        )
        .filter(Q(track__stream_file_low__gt="") | Q(track__stream_file_high__gt=""))
        .values("playlist")
        .annotate(count=Count("id"), duration=Sum("track__duration_seconds"))
    )
    chapter_metrics = (
        AudioTrack.objects.published()
        .filter(work__playlist_items__playlist=OuterRef("pk"))
        .filter(Q(stream_file_low__gt="") | Q(stream_file_high__gt=""))
        .values("work__playlist_items__playlist")
        .annotate(count=Count("id"), duration=Sum("duration_seconds"))
    )
    queryset = (
        Playlist.objects.select_related("owner")
        .annotate(
            directTrackCount=Coalesce(Subquery(direct_metrics.values("count")[:1]), 0),
            chapterTrackCount=Coalesce(
                Subquery(chapter_metrics.values("count")[:1]), 0
            ),
            directDuration=Coalesce(Subquery(direct_metrics.values("duration")[:1]), 0),
            chapterDuration=Coalesce(
                Subquery(chapter_metrics.values("duration")[:1]), 0
            ),
            trackCount=Coalesce(Subquery(direct_metrics.values("count")[:1]), 0)
            + Coalesce(Subquery(chapter_metrics.values("count")[:1]), 0),
            totalDuration=Coalesce(
                Subquery(
                    direct_metrics.values("duration")[:1], output_field=IntegerField()
                ),
                0,
            )
            + Coalesce(
                Subquery(
                    chapter_metrics.values("duration")[:1], output_field=IntegerField()
                ),
                0,
            ),
        )
        .order_by("-created_at", "id")
    )
    if include_tracks:
        queryset = queryset.prefetch_related(
            Prefetch("items", queryset=playable_items),
        )
    return queryset


class PlaylistListCreateView(ListCreateAPIView):
    def get_permissions(self):
        return [AllowAny()] if self.request.method == "GET" else [IsAuthenticated()]

    def get_serializer_class(self):
        if self.request.method == "GET":
            return CompactPlaylistSerializer
        return PlaylistWriteSerializer

    def get_queryset(self):
        queryset = playlist_queryset(include_tracks=False)
        if self.request.query_params.get("mine", "").lower() in {
            "1",
            "true",
            "yes",
        }:
            if not self.request.user.is_authenticated:
                raise NotAuthenticated("Authentication is required.")
            return queryset.filter(
                owner=self.request.user,
                playlist_type=PlaylistType.USER,
            )
        return queryset.filter(
            visibility=PlaylistVisibility.PUBLIC,
            is_published=True,
        ).exclude(playlist_type=PlaylistType.USER)

    def perform_create(self, serializer):
        serializer.save()

    def create(self, request, *args, **kwargs):
        del args, kwargs
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        playlist = serializer.save()
        output = PlaylistDetailSerializer(
            playlist_queryset().get(pk=playlist.pk),
            context=self.get_serializer_context(),
        )
        return Response(output.data, status=status.HTTP_201_CREATED)


class FeaturedPlaylistListView(PublicListCacheMixin, PlaylistListCreateView):
    cache_namespace = "featured-playlists"
    cache_timeout = settings.FEATURED_CACHE_TIMEOUT
    http_method_names = ["get", "head", "options"]

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(
                is_featured=True,
                playlist_type=PlaylistType.EDITORIAL,
            )
        )


class PlaylistDetailView(PublicDetailCacheMixin, RetrieveUpdateDestroyAPIView):
    cache_namespace = "playlist-detail"
    cache_timeout = settings.PUBLIC_DETAIL_CACHE_TIMEOUT
    lookup_field = "slug"
    lookup_url_kwarg = "slug"
    permission_classes = [CanManagePlaylist]

    def get_serializer_class(self):
        return (
            PlaylistDetailSerializer
            if self.request.method == "GET"
            else PlaylistWriteSerializer
        )

    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return super().get_permissions()

    def get_queryset(self):
        queryset = playlist_queryset()
        user = self.request.user
        visible = (
            Q(is_published=True)
            & ~Q(visibility=PlaylistVisibility.PRIVATE)
            & ~Q(playlist_type=PlaylistType.USER)
        )
        if user.is_authenticated:
            visible |= Q(owner=user)
            if user.is_staff:
                visible |= ~Q(playlist_type=PlaylistType.USER)
        return queryset.filter(visible)

    def should_cache_object(self, obj):
        return obj.is_published and obj.visibility == PlaylistVisibility.PUBLIC

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        playlist = playlist_queryset().get(pk=self.get_object().pk)
        notification_service.playlist_updated(playlist)
        return Response(
            PlaylistDetailSerializer(
                playlist,
                context=self.get_serializer_context(),
            ).data,
            status=response.status_code,
        )


class PlaylistActionView(GenericAPIView):
    permission_classes = [IsAuthenticated, CanManagePlaylist]

    def get_playlist(self, slug):
        playlist = get_object_or_404(playlist_queryset(), slug=slug)
        self.check_object_permissions(self.request, playlist)
        return playlist

    def output(self, playlist, *, status_code=status.HTTP_200_OK):
        refreshed = playlist_queryset().get(pk=playlist.pk)
        return Response(
            PlaylistDetailSerializer(
                refreshed,
                context={"request": self.request},
            ).data,
            status=status_code,
        )


class AddTrackView(PlaylistActionView):
    serializer_class = AddTrackSerializer

    def post(self, request, slug):
        playlist = self.get_playlist(slug)
        serializer = self.get_serializer(
            data=request.data,
            context={**self.get_serializer_context(), "playlist": playlist},
        )
        serializer.is_valid(raise_exception=True)
        playlist_item_service.add(
            playlist=playlist,
            track=serializer.validated_data["track"],
            user=request.user,
        )
        return self.output(playlist, status_code=status.HTTP_201_CREATED)


class RemoveTrackView(PlaylistActionView):
    serializer_class = RemoveTrackSerializer

    def remove(self, request, slug):
        playlist = self.get_playlist(slug)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        playlist_item_service.remove(
            playlist=playlist,
            track=serializer.validated_data["track"],
            actor=request.user,
        )
        return self.output(playlist)

    post = remove
    delete = remove


class AddWorkView(PlaylistActionView):
    serializer_class = AddWorkSerializer

    def post(self, request, slug):
        playlist = self.get_playlist(slug)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        playlist_item_service.add_work(
            playlist=playlist, work=serializer.validated_data["work"], user=request.user
        )
        return self.output(playlist, status_code=status.HTTP_201_CREATED)


class RemoveWorkView(PlaylistActionView):
    serializer_class = RemoveWorkSerializer

    def remove(self, request, slug):
        playlist = self.get_playlist(slug)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        playlist_item_service.remove_work(
            playlist=playlist,
            work=serializer.validated_data["work"],
            actor=request.user,
        )
        return self.output(playlist)

    post = remove
    delete = remove


class ReorderTracksView(PlaylistActionView):
    serializer_class = ReorderTracksSerializer

    def reorder(self, request, slug):
        playlist = self.get_playlist(slug)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        playlist_item_service.reorder(
            playlist=playlist,
            track_ids=serializer.validated_data["trackIds"],
            actor=request.user,
        )
        return self.output(playlist)

    post = reorder
    patch = reorder


class ChangeVisibilityView(PlaylistActionView):
    serializer_class = VisibilitySerializer

    def patch(self, request, slug):
        playlist = self.get_playlist(slug)
        serializer = self.get_serializer(
            data=request.data,
            context={**self.get_serializer_context(), "playlist": playlist},
        )
        serializer.is_valid(raise_exception=True)
        playlist.visibility = serializer.validated_data["visibility"]
        playlist.save(update_fields=["visibility", "updated_at"])
        notification_service.playlist_updated(playlist)
        return self.output(playlist)


class DuplicatePlaylistView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = DuplicatePlaylistSerializer

    def post(self, request, slug):
        visible = (
            Q(is_published=True)
            & ~Q(visibility=PlaylistVisibility.PRIVATE)
            & ~Q(playlist_type=PlaylistType.USER)
        ) | Q(owner=request.user)
        source = get_object_or_404(
            playlist_queryset().filter(visible),
            slug=slug,
        )
        serializer = self.get_serializer(
            data=request.data,
            context={"request": request, "source": source},
        )
        serializer.is_valid(raise_exception=True)
        duplicate = serializer.save()
        return Response(
            PlaylistDetailSerializer(
                playlist_queryset().get(pk=duplicate.pk),
                context={"request": request},
            ).data,
            status=status.HTTP_201_CREATED,
        )
