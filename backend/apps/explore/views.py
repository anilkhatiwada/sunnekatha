from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter
from rest_framework.generics import GenericAPIView, ListAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.catalog.track_serializers import CompactTrackSerializer
from apps.catalog.track_views import public_track_queryset
from apps.explore.filters import ExploreTrackFilter
from apps.explore.serializers import ExploreResponseSerializer
from apps.explore.service import explore_service


class ExploreView(GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = ExploreResponseSerializer

    def get(self, request):
        return Response(explore_service.compose())


class ExploreTrackListView(ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = CompactTrackSerializer
    filterset_class = ExploreTrackFilter
    filter_backends = (DjangoFilterBackend, OrderingFilter)
    ordering_fields = (
        "title_ne",
        "title_en",
        "published_at",
        "play_count_cache",
        "duration_seconds",
        "created_at",
    )
    ordering = ("-published_at", "-created_at", "id")

    def get_queryset(self):
        return public_track_queryset()
