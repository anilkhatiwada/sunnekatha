from django.db.models import Count, IntegerField, OuterRef, Prefetch, Q, Subquery, Sum
from django.db.models.functions import Coalesce
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.filters import AlbumFilter, LiteraryWorkFilter
from apps.catalog.models import Album, AudioTrack, LiteraryWork
from apps.catalog.search import TitleFullTextSearchFilter
from apps.catalog.serializers import (
    AlbumSerializer,
    CatalogItemSerializer,
    CompactAlbumSerializer,
    CompactLiteraryWorkSerializer,
    LiteraryWorkSerializer,
)
from apps.catalog.track_views import public_track_queryset


class CatalogQueryMixin:
    permission_classes = [AllowAny]
    filter_backends = (
        DjangoFilterBackend,
        TitleFullTextSearchFilter,
        OrderingFilter,
    )


def literary_work_queryset(*, include_chapters=False):
    playable_chapters = (
        AudioTrack.objects.published()
        .filter(work=OuterRef("pk"))
        .filter(Q(stream_file_low__gt="") | Q(stream_file_high__gt=""))
        .values("work")
        .annotate(count=Count("id"), duration=Sum("duration_seconds"))
    )
    chapters = (
        AudioTrack.objects.published()
        .filter(Q(stream_file_low__gt="") | Q(stream_file_high__gt=""))
        .select_related(
            "work", "work__category", "work__author", "album", "narrator", "language"
        )
        .prefetch_related("work__genres", "work__moods", "work__tags")
        .order_by("chapter_number", "track_number", "published_at", "id")
    )
    queryset = (
        LiteraryWork.objects.published()
        .select_related("author", "language", "category")
        .prefetch_related("genres", "moods", "categories", "tags")
        .annotate(
            playable_chapter_count=Coalesce(
                Subquery(
                    playable_chapters.values("count")[:1],
                    output_field=IntegerField(),
                ),
                0,
            ),
            playable_total_duration=Coalesce(
                Subquery(
                    playable_chapters.values("duration")[:1],
                    output_field=IntegerField(),
                ),
                0,
            ),
        )
    )
    if include_chapters:
        queryset = queryset.prefetch_related(
            Prefetch("audio_tracks", queryset=chapters, to_attr="public_chapters")
        )
    return queryset


class LiteraryWorkListView(CatalogQueryMixin, ListAPIView):
    serializer_class = CompactLiteraryWorkSerializer
    filterset_class = LiteraryWorkFilter
    ordering_fields = (
        "title_ne",
        "title_en",
        "publication_year",
        "published_at",
        "created_at",
        "updated_at",
    )

    def get_queryset(self):
        return literary_work_queryset().defer(
            "description_ne",
            "description_en",
            "copyright_owner",
            "license_notes",
        )


class FeaturedLiteraryWorkListView(LiteraryWorkListView):
    def get_queryset(self):
        return super().get_queryset().filter(is_featured=True)


class LiteraryWorkDetailView(CatalogQueryMixin, RetrieveAPIView):
    serializer_class = LiteraryWorkSerializer
    lookup_field = "slug"
    lookup_url_kwarg = "slug"

    def get_queryset(self):
        return literary_work_queryset(include_chapters=True)


class CatalogItemListView(APIView):
    """Mixed discovery feed: standalone tracks plus serialized parent works."""

    permission_classes = [AllowAny]

    def get(self, request):
        try:
            page = max(1, int(request.query_params.get("page", 1)))
            page_size = min(50, max(1, int(request.query_params.get("pageSize", 20))))
        except (TypeError, ValueError):
            page, page_size = 1, 20

        category = request.query_params.get("category") or request.query_params.get(
            "contentType"
        )
        tag = request.query_params.get("tag")
        author = request.query_params.get("author")
        genre = request.query_params.get("genre")
        mood = request.query_params.get("mood")
        language = request.query_params.get("language")
        narrator = request.query_params.get("narrator")
        premium = request.query_params.get("premium")
        explicit = request.query_params.get("explicit")
        tracks = (
            public_track_queryset()
            .discoverable()
            .defer(
                "description_ne",
                "description_en",
                "transcript",
                "waveform_data",
                "audio_master_file",
                "stream_file_high",
                "stream_file_low",
            )
        )
        works = (
            literary_work_queryset()
            .discoverable()
            .defer(
                "description_ne", "description_en", "copyright_owner", "license_notes"
            )
        )
        if category:
            tracks = tracks.filter(
                Q(work__category__slug=category) | Q(work__categories__slug=category)
            ).distinct()
            works = works.filter(
                Q(category__slug=category) | Q(categories__slug=category)
            ).distinct()
        if tag:
            tracks = tracks.filter(work__tags__slug=tag).distinct()
            works = works.filter(tags__slug=tag).distinct()
        if author:
            tracks = tracks.filter(work__author__slug=author)
            works = works.filter(author__slug=author)
        if genre:
            tracks = tracks.filter(work__genres__slug=genre).distinct()
            works = works.filter(genres__slug=genre).distinct()
        if mood:
            tracks = tracks.filter(work__moods__slug=mood).distinct()
            works = works.filter(moods__slug=mood).distinct()
        if language:
            tracks = tracks.filter(language__slug=language)
            works = works.filter(language__slug=language)
        if narrator:
            tracks = tracks.filter(narrator__slug=narrator)
            works = works.filter(audio_tracks__narrator__slug=narrator).distinct()
        if premium in {"true", "false"}:
            value = premium == "true"
            tracks = tracks.filter(is_premium=value)
            works = works.filter(audio_tracks__is_premium=value).distinct()
        if explicit in {"true", "false"}:
            value = explicit == "true"
            tracks = tracks.filter(is_explicit=value)
            works = works.filter(audio_tracks__is_explicit=value).distinct()

        # This endpoint is intentionally bounded. It creates a stable mixed page
        # without materializing the full catalog in application memory.
        window_end = page * page_size
        track_rows = list(tracks.order_by("-published_at", "id")[:window_end])
        work_rows = list(works.order_by("-published_at", "id")[:window_end])
        items = [
            *({"kind": "track", "content": item} for item in track_rows),
            *({"kind": "work", "content": item} for item in work_rows),
        ]
        items.sort(
            key=lambda item: (
                item["content"].published_at,
                str(item["content"].pk),
            ),
            reverse=True,
        )
        start = (page - 1) * page_size
        count = tracks.count() + works.count()
        results = CatalogItemSerializer(
            items[start : start + page_size], many=True, context={"request": request}
        ).data
        base = request.build_absolute_uri(request.path)
        return Response(
            {
                "count": count,
                "next": f"{base}?page={page + 1}&pageSize={page_size}"
                if start + page_size < count
                else None,
                "previous": f"{base}?page={page - 1}&pageSize={page_size}"
                if page > 1
                else None,
                "results": results,
            }
        )


class AlbumListView(CatalogQueryMixin, ListAPIView):
    serializer_class = CompactAlbumSerializer
    filterset_class = AlbumFilter
    ordering_fields = (
        "title_ne",
        "title_en",
        "release_date",
        "created_at",
        "updated_at",
    )

    def get_queryset(self):
        return (
            Album.objects.published()
            .select_related("author")
            .prefetch_related("genres", "moods")
            .defer("description_ne", "description_en")
        )


class FeaturedAlbumListView(AlbumListView):
    def get_queryset(self):
        return super().get_queryset().filter(is_featured=True)


class AlbumDetailView(CatalogQueryMixin, RetrieveAPIView):
    serializer_class = AlbumSerializer
    lookup_field = "slug"
    lookup_url_kwarg = "slug"

    def get_queryset(self):
        return (
            Album.objects.published()
            .select_related("author")
            .prefetch_related("genres", "moods")
        )
