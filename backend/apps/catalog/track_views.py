from django.conf import settings
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.models import AudioTrack, TrackProcessingStatus
from apps.catalog.track_filters import AudioTrackFilter
from apps.catalog.track_serializers import (
    CompactTrackSerializer,
    DetailedTrackSerializer,
    PlayerTrackSerializer,
)
from apps.common.cache_views import PublicDetailCacheMixin
from apps.common.schema import with_standard_errors
from apps.media_access.serializers import (
    StreamQuerySerializer,
    StreamResponseSerializer,
)
from apps.media_access.services import cloudfront_media_service


def public_track_queryset():
    return (
        AudioTrack.objects.published()
        .select_related(
            "work",
            "work__category",
            "work__author",
            "album",
            "narrator",
            "language",
        )
        .prefetch_related("work__genres", "work__moods")
    )


class TrackListView(ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = CompactTrackSerializer
    filterset_class = AudioTrackFilter
    filter_backends = (DjangoFilterBackend, SearchFilter, OrderingFilter)
    search_fields = ("title_ne", "title_en", "description_ne", "description_en")
    ordering_fields = (
        "title_ne",
        "title_en",
        "published_at",
        "play_count_cache",
        "duration_seconds",
        "track_number",
        "created_at",
    )
    ordering = ("-published_at", "title_ne", "id")

    def get_queryset(self):
        queryset = public_track_queryset()
        # Work detail pages explicitly request their chapters. Everywhere else,
        # serialized chapters are represented by their parent literary work.
        if not self.request.query_params.get("work"):
            queryset = queryset.discoverable()
        return queryset.defer(
            "description_ne",
            "description_en",
            "transcript",
            "waveform_data",
            "audio_master_file",
            "stream_file_high",
            "stream_file_low",
        )


class FeaturedTrackListView(TrackListView):
    def get_queryset(self):
        return super().get_queryset().filter(is_featured=True)


class TrendingTrackListView(TrackListView):
    ordering = ("-play_count_cache", "-published_at", "id")


class RecentlyAddedTrackListView(TrackListView):
    ordering = ("-published_at", "-created_at", "id")


class TrackRelationListView(TrackListView):
    relation_lookup = ""
    url_kwarg = "slug"

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return super().get_queryset()
        value = self.kwargs[self.url_kwarg]
        return super().get_queryset().filter(**{self.relation_lookup: value})


class TracksByContentTypeView(TrackRelationListView):
    relation_lookup = "work__category__slug"
    url_kwarg = "content_type"


class TracksByAuthorView(TrackRelationListView):
    relation_lookup = "work__author__slug"


class TracksByNarratorView(TrackRelationListView):
    relation_lookup = "narrator__slug"


class TracksByGenreView(TrackRelationListView):
    relation_lookup = "work__genres__slug"

    def get_queryset(self):
        return super().get_queryset().distinct()


class TracksByMoodView(TrackRelationListView):
    relation_lookup = "work__moods__slug"

    def get_queryset(self):
        return super().get_queryset().distinct()


class TrackDetailView(PublicDetailCacheMixin, RetrieveAPIView):
    cache_namespace = "track-detail"
    cache_timeout = settings.PUBLIC_DETAIL_CACHE_TIMEOUT
    permission_classes = [AllowAny]
    serializer_class = DetailedTrackSerializer
    lookup_field = "slug"
    lookup_url_kwarg = "slug"

    def get_queryset(self):
        return public_track_queryset()


class PlayerTrackView(RetrieveAPIView):
    permission_classes = [AllowAny]
    serializer_class = PlayerTrackSerializer
    lookup_field = "slug"
    lookup_url_kwarg = "slug"

    def get_queryset(self):
        return public_track_queryset()


class TrackStreamView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = "stream"

    @extend_schema(
        summary="Authorize track streaming",
        description=(
            "Returns media authorization metadata and a CloudFront URL; Django "
            "never proxies audio bytes. Free published tracks are available to "
            "everyone. Premium tracks require an active entitlement. Premium URLs "
            "are signed and short-lived; clients must not persist or share them. "
            "Unpublished tracks are restricted to authorized staff or creators."
        ),
        parameters=[StreamQuerySerializer],
        responses=with_standard_errors({200: StreamResponseSerializer}),
        examples=[
            OpenApiExample(
                "Premium signed stream",
                value={
                    "quality": "high",
                    "url": "https://media.example.com/opaque/audio.m4a?Policy=...",
                    "expiresAt": "2026-07-23T17:05:00Z",
                    "track": {
                        "id": "f60f09ad-7bc5-4cf0-8368-b199aa076d59",
                        "slug": "seto-dharti",
                        "title": "सेतो धरती",
                        "duration": 842,
                        "isPremium": True,
                    },
                    "authorization": {
                        "status": "authorized",
                        "accessType": "premium",
                        "isEntitled": True,
                        "isPrivileged": False,
                    },
                },
                response_only=True,
            )
        ],
        tags=["tracks"],
    )
    def get(self, request, slug):
        track = get_object_or_404(
            AudioTrack.objects.filter(
                processing_status=TrackProcessingStatus.READY,
            )
            .select_related(
                "work",
                "work__author",
                "album",
                "narrator",
                "narrator__user",
                "language",
            )
            .prefetch_related("work__genres", "work__moods"),
            slug=slug,
        )
        query = StreamQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        payload = cloudfront_media_service.deliver(
            track,
            quality=query.validated_data["quality"],
            request=request,
        )
        payload["introduction"] = (
            cloudfront_media_service.deliver_introduction(track, request=request)
            if query.validated_data["includeIntroduction"]
            else None
        )
        payload["track"] = track
        return Response(
            StreamResponseSerializer(
                payload,
                context={"request": request},
            ).data
        )


class RelatedTrackListView(TrackListView):
    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return super().get_queryset()
        source = get_object_or_404(
            public_track_queryset(),
            slug=self.kwargs["slug"],
        )
        genre_ids = source.work.genres.values_list("id", flat=True)
        mood_ids = source.work.moods.values_list("id", flat=True)
        return (
            public_track_queryset()
            .discoverable()
            .exclude(pk=source.pk)
            .filter(
                Q(work__category=source.work.category)
                | Q(work__author_id=source.work.author_id)
                | Q(work__genres__id__in=genre_ids)
                | Q(work__moods__id__in=mood_ids)
            )
            .distinct()
            .order_by("-is_featured", "-play_count_cache", "-published_at", "id")
        )
