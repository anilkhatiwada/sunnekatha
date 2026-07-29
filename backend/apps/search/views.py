from drf_spectacular.utils import extend_schema
from rest_framework.generics import GenericAPIView, ListAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.catalog.track_serializers import CompactTrackSerializer
from apps.catalog.track_views import public_track_queryset
from apps.search.models import SearchAlias
from apps.search.serializers import (
    AutocompleteItemSerializer,
    GroupedSearchResponseSerializer,
    SearchQuerySerializer,
    TrendingSearchResponseSerializer,
)
from apps.search.service import TRENDING_SEARCHES, search_service


class SearchParametersMixin:
    def parameters(self):
        serializer = SearchQuerySerializer(data=self.request.query_params)
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data


class GroupedSearchView(SearchParametersMixin, GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = GroupedSearchResponseSerializer

    @extend_schema(parameters=[SearchQuerySerializer])
    def get(self, request):
        parameters = self.parameters()
        return Response(
            search_service.grouped(
                parameters["q"].strip(),
                result_type=parameters["type"],
                content_type=parameters.get("content_type"),
                context={"request": request},
            )
        )


class TrackSearchView(SearchParametersMixin, ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = CompactTrackSerializer

    @extend_schema(parameters=[SearchQuerySerializer])
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        parameters = self.parameters()
        query = parameters["q"].strip()
        if not query:
            return public_track_queryset().none()
        return search_service.querysets(
            query,
            content_type=parameters.get("content_type"),
        )["tracks"]


class AutocompleteView(SearchParametersMixin, GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = AutocompleteItemSerializer
    queryset = SearchAlias.objects.none()

    @extend_schema(
        parameters=[SearchQuerySerializer],
        responses=AutocompleteItemSerializer(many=True),
    )
    def get(self, request):
        query = self.parameters()["q"].strip()
        serializer = self.get_serializer(
            search_service.autocomplete(query),
            many=True,
        )
        return Response(serializer.data)


class TrendingSearchView(GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = TrendingSearchResponseSerializer

    def get(self, request):
        del request
        return Response({"searches": TRENDING_SEARCHES})
