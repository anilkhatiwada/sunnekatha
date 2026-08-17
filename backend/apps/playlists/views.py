from django.conf import settings
from django.db.models import Count, Prefetch, Q, Sum
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

from apps.catalog.models import TrackProcessingStatus
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
    CompactPlaylistSerializer,
    DuplicatePlaylistSerializer,
    PlaylistDetailSerializer,
    PlaylistWriteSerializer,
    RemoveTrackSerializer,
    ReorderTracksSerializer,
    VisibilitySerializer,
)
from apps.playlists.services import playlist_item_service


def playlist_queryset(*, include_tracks=True):
    playable = Q(
        items__track__is_published=True,
        items__track__processing_status=TrackProcessingStatus.READY,
        items__track__published_at__lte=timezone.now(),
    ) & (
        Q(items__track__stream_file_low__gt="")
        | Q(items__track__stream_file_high__gt="")
    )
    playable_items = (
        PlaylistItem.objects.filter(
            track__is_published=True,
            track__processing_status=TrackProcessingStatus.READY,
            track__published_at__lte=timezone.now(),
        )
        .filter(Q(track__stream_file_low__gt="") | Q(track__stream_file_high__gt=""))
        .select_related(
            "track__work__author",
            "track__work__category",
            "track__album",
            "track__narrator",
            "track__language",
        )
        .prefetch_related("track__work__genres", "track__work__moods")
        .order_by("position", "created_at", "id")
    )
    queryset = (
        Playlist.objects.select_related("owner")
        .annotate(
            trackCount=Count("items", filter=playable),
            totalDuration=Coalesce(
                Sum("items__track__duration_seconds", filter=playable),
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
