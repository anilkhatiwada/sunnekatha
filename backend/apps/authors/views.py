from django.conf import settings
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import AllowAny

from apps.authors.filters import AuthorFilter
from apps.authors.models import Author
from apps.authors.serializers import AuthorSerializer, CompactAuthorSerializer
from apps.common.cache_views import PublicListCacheMixin


class AuthorListView(ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = CompactAuthorSerializer
    filterset_class = AuthorFilter
    filter_backends = (DjangoFilterBackend, SearchFilter, OrderingFilter)
    search_fields = (
        "name_ne",
        "name_en",
        "biography_ne",
        "biography_en",
        "country",
    )
    ordering_fields = (
        "name_ne",
        "name_en",
        "birth_date",
        "created_at",
        "updated_at",
    )
    ordering = ("name_ne", "id")

    def get_queryset(self):
        return Author.objects.defer("biography_ne", "biography_en")


class FeaturedAuthorListView(PublicListCacheMixin, AuthorListView):
    cache_namespace = "featured-authors"
    cache_timeout = settings.FEATURED_CACHE_TIMEOUT

    def get_queryset(self):
        return (
            Author.objects.filter(is_featured=True)
            .defer(
                "biography_ne",
                "biography_en",
            )
            .order_by(
                "-is_verified",
                "name_ne",
                "id",
            )
        )


class AuthorDetailView(RetrieveAPIView):
    permission_classes = [AllowAny]
    serializer_class = AuthorSerializer
    lookup_field = "slug"
    lookup_url_kwarg = "slug"

    def get_queryset(self):
        return Author.objects.all()
