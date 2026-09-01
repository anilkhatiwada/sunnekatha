from django.conf import settings
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny

from apps.common.cache_views import PublicListCacheMixin
from apps.taxonomy.filters import ActiveTaxonomyFilter
from apps.taxonomy.models import ContentCategory, Genre, Language, Mood, Tag
from apps.taxonomy.serializers import (
    ContentCategorySerializer,
    GenreSerializer,
    LanguageSerializer,
    MoodSerializer,
    TagSerializer,
)


class TaxonomyListView(ListAPIView):
    permission_classes = [AllowAny]
    pagination_class = None
    filterset_class = ActiveTaxonomyFilter
    filter_backends = (DjangoFilterBackend, SearchFilter, OrderingFilter)
    search_fields = ("name_ne", "name_en", "description")
    ordering_fields = ("sort_order", "name_ne", "name_en", "created_at")
    ordering = ("sort_order", "name_ne", "id")


class GenreListView(PublicListCacheMixin, TaxonomyListView):
    cache_namespace = "genres"
    cache_timeout = settings.TAXONOMY_CACHE_TIMEOUT
    queryset = Genre.objects.all()
    serializer_class = GenreSerializer


class MoodListView(PublicListCacheMixin, TaxonomyListView):
    cache_namespace = "moods"
    cache_timeout = settings.TAXONOMY_CACHE_TIMEOUT
    queryset = Mood.objects.all()
    serializer_class = MoodSerializer


class LanguageListView(TaxonomyListView):
    queryset = Language.objects.all()
    serializer_class = LanguageSerializer


class ContentCategoryListView(PublicListCacheMixin, TaxonomyListView):
    cache_namespace = "content-categories"
    cache_timeout = settings.TAXONOMY_CACHE_TIMEOUT
    queryset = ContentCategory.objects.all()
    serializer_class = ContentCategorySerializer


class TagListView(PublicListCacheMixin, TaxonomyListView):
    cache_namespace = "tags"
    cache_timeout = settings.TAXONOMY_CACHE_TIMEOUT
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
