from collections import defaultdict

from django.contrib.postgres.search import (
    SearchQuery,
    SearchRank,
    SearchVector,
    TrigramSimilarity,
)
from django.db import connection
from django.db.models import Q
from django.db.models.functions import Greatest

from apps.authors.models import Author
from apps.authors.serializers import CompactAuthorSerializer
from apps.catalog.models import Album, LiteraryWork
from apps.catalog.serializers import (
    CompactAlbumSerializer,
    CompactLiteraryWorkSerializer,
)
from apps.catalog.track_serializers import CompactTrackSerializer
from apps.catalog.track_views import public_track_queryset
from apps.narrators.models import Narrator
from apps.narrators.serializers import CompactNarratorSerializer
from apps.playlists.models import PlaylistVisibility
from apps.playlists.serializers import CompactPlaylistSerializer
from apps.playlists.views import playlist_queryset
from apps.search.models import SearchAlias, SearchEntityType, normalize_alias
from apps.taxonomy.models import Genre, Mood
from apps.taxonomy.serializers import GenreSerializer, MoodSerializer

GROUP_LIMIT = 8
AUTOCOMPLETE_LIMIT = 10
TRENDING_SEARCHES = (
    "प्रेमका कविता",
    "वर्षाको साँझ",
    "नेपाली लोककथा",
    "जीवन र दर्शन",
    "बालकथा",
    "शान्त",
)


def matching_aliases(query):
    normalized = normalize_alias(query)
    aliases = SearchAlias.objects.all()
    if connection.vendor == "postgresql":
        aliases = (
            aliases.annotate(
                similarity=TrigramSimilarity("normalized_alias", normalized)
            )
            .filter(
                Q(normalized_alias__unaccent__icontains=normalized)
                | Q(similarity__gte=0.2)
            )
            .order_by("-similarity", "normalized_alias")
        )
    else:
        aliases = aliases.filter(normalized_alias__icontains=normalized)
    result = defaultdict(set)
    for alias in aliases:
        result[alias.entity_type].add(alias.object_id)
    return result


def ranked_search(
    queryset,
    *,
    query,
    primary_fields,
    secondary_fields=(),
    alias_filter=None,
):
    fields = (*primary_fields, *secondary_fields)
    text_filter = Q()
    for field in fields:
        lookup = (
            f"{field}__unaccent__icontains"
            if connection.vendor == "postgresql"
            else f"{field}__icontains"
        )
        text_filter |= Q(**{lookup: query})
    if alias_filter:
        text_filter |= alias_filter

    if connection.vendor != "postgresql":
        return queryset.filter(text_filter).distinct()

    local_secondary_fields = tuple(
        field for field in secondary_fields if "__" not in field
    )
    vector = SearchVector(*primary_fields, weight="A", config="simple")
    if local_secondary_fields:
        vector += SearchVector(
            *local_secondary_fields,
            weight="B",
            config="simple",
        )
    search_query = SearchQuery(query, config="simple", search_type="websearch")
    similarity = Greatest(
        *[TrigramSimilarity(field, query) for field in primary_fields]
    )
    return (
        queryset.annotate(
            search_document=vector,
            search_rank=SearchRank(vector, search_query),
            search_similarity=similarity,
        )
        .filter(
            Q(search_document=search_query)
            | Q(search_similarity__gte=0.15)
            | text_filter
        )
        .order_by("-search_rank", "-search_similarity", "id")
        .distinct()
    )


def alias_q(aliases, mappings):
    condition = Q()
    for entity_type, lookup in mappings.items():
        object_ids = aliases.get(entity_type)
        if object_ids:
            condition |= Q(**{f"{lookup}__in": object_ids})
    return condition


class SearchService:
    def querysets(self, query, *, content_type=None):
        aliases = matching_aliases(query)
        tracks = ranked_search(
            public_track_queryset().defer(
                "description_ne",
                "description_en",
                "transcript",
                "waveform_data",
                "audio_master_file",
                "stream_file_high",
                "stream_file_low",
            ),
            query=query,
            primary_fields=("title_ne", "title_en"),
            secondary_fields=(
                "description_ne",
                "description_en",
                "work__title_ne",
                "work__title_en",
                "work__author__name_ne",
                "work__author__name_en",
                "narrator__name_ne",
                "narrator__name_en",
                "work__genres__name_ne",
                "work__genres__name_en",
                "work__moods__name_ne",
                "work__moods__name_en",
            ),
            alias_filter=alias_q(
                aliases,
                {
                    SearchEntityType.TRACK: "id",
                    SearchEntityType.LITERARY_WORK: "work_id",
                    SearchEntityType.AUTHOR: "work__author_id",
                    SearchEntityType.NARRATOR: "narrator_id",
                    SearchEntityType.GENRE: "work__genres__id",
                    SearchEntityType.MOOD: "work__moods__id",
                },
            ),
        )
        works = ranked_search(
            LiteraryWork.objects.published()
            .select_related("author", "language")
            .prefetch_related("genres", "moods")
            .defer(
                "description_ne",
                "description_en",
                "copyright_owner",
                "license_notes",
            ),
            query=query,
            primary_fields=("title_ne", "title_en", "subtitle_ne", "subtitle_en"),
            secondary_fields=(
                "description_ne",
                "description_en",
                "author__name_ne",
                "author__name_en",
                "genres__name_ne",
                "moods__name_ne",
            ),
            alias_filter=alias_q(
                aliases,
                {
                    SearchEntityType.LITERARY_WORK: "id",
                    SearchEntityType.AUTHOR: "author_id",
                    SearchEntityType.GENRE: "genres__id",
                    SearchEntityType.MOOD: "moods__id",
                },
            ),
        )
        if content_type:
            tracks = tracks.filter(content_type=content_type)
            works = works.filter(content_type=content_type)
        return {
            "tracks": tracks,
            "literaryWorks": works,
            "playlists": ranked_search(
                playlist_queryset(include_tracks=False).filter(
                    visibility=PlaylistVisibility.PUBLIC,
                    is_published=True,
                ),
                query=query,
                primary_fields=("title_ne", "title_en"),
                secondary_fields=("description_ne", "description_en"),
                alias_filter=alias_q(aliases, {SearchEntityType.PLAYLIST: "id"}),
            ),
            "albums": ranked_search(
                Album.objects.published()
                .select_related("author")
                .prefetch_related("genres", "moods")
                .defer("description_ne", "description_en"),
                query=query,
                primary_fields=("title_ne", "title_en"),
                secondary_fields=(
                    "description_ne",
                    "description_en",
                    "author__name_ne",
                    "author__name_en",
                    "genres__name_ne",
                    "moods__name_ne",
                ),
                alias_filter=alias_q(
                    aliases,
                    {
                        SearchEntityType.ALBUM: "id",
                        SearchEntityType.AUTHOR: "author_id",
                        SearchEntityType.GENRE: "genres__id",
                        SearchEntityType.MOOD: "moods__id",
                    },
                ),
            ),
            "authors": ranked_search(
                Author.objects.defer("biography_ne", "biography_en"),
                query=query,
                primary_fields=("name_ne", "name_en"),
                secondary_fields=("biography_ne", "biography_en"),
                alias_filter=alias_q(aliases, {SearchEntityType.AUTHOR: "id"}),
            ),
            "narrators": ranked_search(
                Narrator.objects.select_related("user").defer(
                    "biography_ne",
                    "biography_en",
                ),
                query=query,
                primary_fields=("name_ne", "name_en"),
                secondary_fields=("biography_ne", "biography_en"),
                alias_filter=alias_q(aliases, {SearchEntityType.NARRATOR: "id"}),
            ),
            "genres": ranked_search(
                Genre.objects.filter(is_active=True),
                query=query,
                primary_fields=("name_ne", "name_en"),
                secondary_fields=("description",),
                alias_filter=alias_q(aliases, {SearchEntityType.GENRE: "id"}),
            ),
            "moods": ranked_search(
                Mood.objects.filter(is_active=True),
                query=query,
                primary_fields=("name_ne", "name_en"),
                secondary_fields=("description",),
                alias_filter=alias_q(aliases, {SearchEntityType.MOOD: "id"}),
            ),
        }

    def grouped(self, query, *, result_type="all", content_type=None, context=None):
        serializers = {
            "tracks": CompactTrackSerializer,
            "literaryWorks": CompactLiteraryWorkSerializer,
            "playlists": CompactPlaylistSerializer,
            "albums": CompactAlbumSerializer,
            "authors": CompactAuthorSerializer,
            "narrators": CompactNarratorSerializer,
            "genres": GenreSerializer,
            "moods": MoodSerializer,
        }
        payload = {"query": query}
        if not query:
            payload.update({key: [] for key in serializers})
            return payload
        querysets = self.querysets(query, content_type=content_type)
        selected = "literaryWorks" if result_type == "works" else result_type
        for key, serializer_class in serializers.items():
            items = (
                list(querysets[key][:GROUP_LIMIT]) if selected in {"all", key} else []
            )
            payload[key] = serializer_class(
                items, many=True, context=context or {}
            ).data
        return payload

    def autocomplete(self, query):
        if not query:
            return []
        querysets = self.querysets(query)
        configuration = (
            ("track", "tracks", "title_ne", "title_en"),
            ("work", "literaryWorks", "title_ne", "title_en"),
            ("playlist", "playlists", "title_ne", "title_en"),
            ("album", "albums", "title_ne", "title_en"),
            ("author", "authors", "name_ne", "name_en"),
            ("narrator", "narrators", "name_ne", "name_en"),
            ("genre", "genres", "name_ne", "name_en"),
            ("mood", "moods", "name_ne", "name_en"),
        )
        suggestions = []
        for kind, key, label_field, english_field in configuration:
            for item in querysets[key][:2]:
                suggestions.append(
                    {
                        "type": kind,
                        "id": item.id,
                        "slug": item.slug,
                        "label": getattr(item, label_field),
                        "labelEnglish": getattr(item, english_field),
                    }
                )
                if len(suggestions) == AUTOCOMPLETE_LIMIT:
                    return suggestions
        return suggestions


search_service = SearchService()
