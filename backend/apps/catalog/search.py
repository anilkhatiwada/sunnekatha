from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.db import connection
from django.db.models import Q
from rest_framework.filters import BaseFilterBackend


class TitleFullTextSearchFilter(BaseFilterBackend):
    """PostgreSQL full-text title search with a deterministic SQLite fallback."""

    search_param = "search"

    def filter_queryset(self, request, queryset, view):
        del view
        query = request.query_params.get(self.search_param, "").strip()
        if not query:
            return queryset

        if connection.vendor == "postgresql":
            vector = SearchVector(
                "title_ne",
                weight="A",
                config="simple",
            ) + SearchVector(
                "title_en",
                weight="A",
                config="simple",
            )
            search_query = SearchQuery(query, config="simple", search_type="websearch")
            return (
                queryset.annotate(
                    search_document=vector,
                    search_rank=SearchRank(vector, search_query),
                )
                .filter(search_document=search_query)
                .order_by("-search_rank", "title_ne", "id")
            )

        terms = query.split()
        for term in terms:
            queryset = queryset.filter(
                Q(title_ne__icontains=term) | Q(title_en__icontains=term)
            )
        return queryset
