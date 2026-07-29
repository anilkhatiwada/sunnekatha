from django.conf import settings
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import AllowAny

from apps.common.cache_views import PublicListCacheMixin
from apps.narrators.filters import NarratorFilter
from apps.narrators.models import Narrator
from apps.narrators.serializers import CompactNarratorSerializer, NarratorSerializer


class NarratorListView(ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = CompactNarratorSerializer
    filterset_class = NarratorFilter
    filter_backends = (DjangoFilterBackend, SearchFilter, OrderingFilter)
    search_fields = (
        "name_ne",
        "name_en",
        "biography_ne",
        "biography_en",
        "user__display_name",
        "user__username",
    )
    ordering_fields = (
        "name_ne",
        "name_en",
        "follower_count_cache",
        "created_at",
        "updated_at",
    )
    ordering = ("name_ne", "id")

    def get_queryset(self):
        return Narrator.objects.select_related("user").defer(
            "biography_ne",
            "biography_en",
        )


class FeaturedNarratorListView(PublicListCacheMixin, NarratorListView):
    cache_namespace = "featured-narrators"
    cache_timeout = settings.FEATURED_CACHE_TIMEOUT

    def get_queryset(self):
        return (
            Narrator.objects.filter(is_featured=True)
            .select_related("user")
            .defer("biography_ne", "biography_en")
            .order_by("-is_verified", "-follower_count_cache", "name_ne", "id")
        )


class NarratorDetailView(RetrieveAPIView):
    permission_classes = [AllowAny]
    serializer_class = NarratorSerializer
    lookup_field = "slug"
    lookup_url_kwarg = "slug"

    def get_queryset(self):
        return Narrator.objects.select_related("user")
