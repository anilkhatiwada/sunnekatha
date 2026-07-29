from django.db.models import Count, Q, Sum
from django.utils import timezone

from apps.authors.models import Author
from apps.catalog.models import Album, ContentType, TrackProcessingStatus
from apps.catalog.track_serializers import CompactTrackSerializer
from apps.catalog.track_views import public_track_queryset
from apps.home.serializers import (
    HomeAlbumSerializer,
    HomeAuthorSerializer,
    HomeNarratorSerializer,
    HomePlaylistSerializer,
)
from apps.narrators.models import Narrator
from apps.playlists.models import Playlist, PlaylistType, PlaylistVisibility
from apps.taxonomy.models import Genre, Mood
from apps.taxonomy.serializers import GenreSerializer, MoodSerializer

SECTION_LIMIT = 6
COLLECTION_LIMIT = 12

CONTENT_TYPE_TITLES = {
    ContentType.POEM: "कविता",
    ContentType.STORY: "कथा",
    ContentType.ESSAY: "निबन्ध",
    ContentType.NOVEL_CHAPTER: "उपन्यास",
    ContentType.FOLK_TALE: "लोककथा",
    ContentType.DRAMA: "नाटक",
}


def section(identifier, title, items):
    return {"id": identifier, "title": title, "items": items}


class ExploreService:
    def compose(self):
        playable = Q(
            items__track__is_published=True,
            items__track__processing_status=TrackProcessingStatus.READY,
            items__track__published_at__lte=timezone.now(),
        )
        tracks = public_track_queryset()
        content_counts = {
            row["content_type"]: row["track_count"]
            for row in tracks.values("content_type").annotate(
                track_count=Count("id", distinct=True)
            )
        }
        content_types = [
            {
                "id": value,
                "slug": value,
                "name": CONTENT_TYPE_TITLES[value],
                "nameEnglish": label,
                "trackCount": content_counts.get(value, 0),
            }
            for value, label in ContentType.choices
        ]
        genres = list(
            Genre.objects.filter(is_active=True)
            .annotate(
                trackCount=Count(
                    "literary_works__audio_tracks",
                    filter=Q(
                        literary_works__audio_tracks__is_published=True,
                        literary_works__audio_tracks__processing_status=(
                            TrackProcessingStatus.READY
                        ),
                        literary_works__audio_tracks__published_at__lte=timezone.now(),
                    ),
                    distinct=True,
                )
            )
            .order_by("sort_order", "name_ne", "id")[:COLLECTION_LIMIT]
        )
        moods = list(
            Mood.objects.filter(is_active=True)
            .annotate(
                trackCount=Count(
                    "literary_works__audio_tracks",
                    filter=Q(
                        literary_works__audio_tracks__is_published=True,
                        literary_works__audio_tracks__processing_status=(
                            TrackProcessingStatus.READY
                        ),
                        literary_works__audio_tracks__published_at__lte=timezone.now(),
                    ),
                    distinct=True,
                )
            )
            .order_by("sort_order", "name_ne", "id")[:COLLECTION_LIMIT]
        )
        playlists = list(
            Playlist.objects.filter(
                playlist_type=PlaylistType.EDITORIAL,
                visibility=PlaylistVisibility.PUBLIC,
                is_published=True,
                is_featured=True,
            )
            .select_related("owner")
            .annotate(
                trackCount=Count("items", filter=playable),
                totalDuration=Sum(
                    "items__track__duration_seconds", filter=playable, default=0
                ),
            )
            .order_by("-updated_at", "id")[:SECTION_LIMIT]
        )
        albums = list(
            Album.objects.published()
            .filter(is_featured=True)
            .select_related("author")
            .order_by("-release_date", "-created_at", "id")[:SECTION_LIMIT]
        )
        authors = list(
            Author.objects.annotate(
                popularity=Sum(
                    "literary_works__audio_tracks__play_count_cache",
                    filter=Q(
                        literary_works__audio_tracks__is_published=True,
                        literary_works__audio_tracks__processing_status=(
                            TrackProcessingStatus.READY
                        ),
                        literary_works__audio_tracks__published_at__lte=timezone.now(),
                    ),
                    default=0,
                )
            ).order_by("-popularity", "-is_featured", "-is_verified", "name_ne", "id")[
                :SECTION_LIMIT
            ]
        )
        narrators = list(
            Narrator.objects.order_by(
                "-follower_count_cache",
                "-is_featured",
                "-is_verified",
                "name_ne",
                "id",
            )[:SECTION_LIMIT]
        )
        releases = list(
            tracks.order_by("-published_at", "-created_at", "id")[:SECTION_LIMIT]
        )
        return {
            "sections": [
                section("content-types", "साहित्यका प्रकार", content_types),
                section("genres", "विधाहरू", GenreSerializer(genres, many=True).data),
                section(
                    "moods",
                    "मूडअनुसार सुन्नुहोस्",
                    MoodSerializer(moods, many=True).data,
                ),
                section(
                    "featured-playlists",
                    "विशेष प्लेलिस्टहरू",
                    HomePlaylistSerializer(playlists, many=True).data,
                ),
                section(
                    "featured-albums",
                    "विशेष एल्बमहरू",
                    HomeAlbumSerializer(albums, many=True).data,
                ),
                section(
                    "popular-authors",
                    "लोकप्रिय लेखकहरू",
                    HomeAuthorSerializer(authors, many=True).data,
                ),
                section(
                    "popular-narrators",
                    "लोकप्रिय वाचकहरू",
                    HomeNarratorSerializer(narrators, many=True).data,
                ),
                section(
                    "new-releases",
                    "नयाँ रचना",
                    CompactTrackSerializer(releases, many=True).data,
                ),
            ]
        }


explore_service = ExploreService()
