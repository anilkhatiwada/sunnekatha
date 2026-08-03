from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import AllowAny

from apps.catalog.filters import AlbumFilter, LiteraryWorkFilter
from apps.catalog.models import Album, LiteraryWork
from apps.catalog.search import TitleFullTextSearchFilter
from apps.catalog.serializers import (
    AlbumSerializer,
    CompactAlbumSerializer,
    CompactLiteraryWorkSerializer,
    LiteraryWorkSerializer,
)


class CatalogQueryMixin:
    permission_classes = [AllowAny]
    filter_backends = (
        DjangoFilterBackend,
        TitleFullTextSearchFilter,
        OrderingFilter,
    )


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
        return (
            LiteraryWork.objects.published()
            .select_related("author", "language", "category")
            .prefetch_related("genres", "moods")
            .defer(
                "description_ne",
                "description_en",
                "copyright_owner",
                "license_notes",
            )
        )


class FeaturedLiteraryWorkListView(LiteraryWorkListView):
    def get_queryset(self):
        return super().get_queryset().filter(is_featured=True)


class LiteraryWorkDetailView(CatalogQueryMixin, RetrieveAPIView):
    serializer_class = LiteraryWorkSerializer
    lookup_field = "slug"
    lookup_url_kwarg = "slug"

    def get_queryset(self):
        return (
            LiteraryWork.objects.published()
            .select_related("author", "language", "category")
            .prefetch_related("genres", "moods")
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
