from copy import deepcopy

from django.conf import settings
from django.core.cache import cache
from django.db.models import Count, Q, Sum
from django.utils import timezone

from apps.authors.models import Author
from apps.catalog.models import Album, TrackProcessingStatus
from apps.catalog.track_serializers import CompactTrackSerializer
from apps.catalog.track_views import public_track_queryset
from apps.common.cache import public_cache_keys
from apps.home.models import HomeSection, HomeSectionType
from apps.home.serializers import (
    HomeAlbumSerializer,
    HomeAuthorSerializer,
    HomeGenreSerializer,
    HomeMoodCollectionSerializer,
    HomeNarratorSerializer,
    HomePlaylistSerializer,
)
from apps.library.models import ListeningProgress
from apps.library.serializers import ContinueListeningSerializer
from apps.narrators.models import Narrator
from apps.playlists.models import Playlist, PlaylistType, PlaylistVisibility
from apps.taxonomy.models import Mood

SECTION_LIMIT = 6
CONTINUE_LIMIT = 6
MOOD_LIMIT = 4


def section(identifier, title, items, *, section_type, layout="rail"):
    return {
        "id": identifier,
        "title": title,
        "sectionType": section_type,
        "layout": layout,
        "items": items,
    }


class HomeService:
    def compose(self, *, user):
        payload = deepcopy(self.get_public_payload())
        continue_index = payload.pop("_continueIndex", 0)
        continue_config = payload.pop("_continueSection", None)
        if user and user.is_authenticated and user.is_active:
            payload["sections"].insert(
                continue_index,
                self.get_continue_section(user, configuration=continue_config),
            )
        return payload

    def get_public_payload(self):
        key = public_cache_keys.key("home")
        cached = cache.get(key)
        if cached is not None:
            return cached
        payload = self.build_public_payload()
        cache.set(
            key,
            payload,
            timeout=settings.HOME_PUBLIC_CACHE_TIMEOUT,
        )
        return payload

    def build_public_payload(self):
        editorial_sections = list(
            HomeSection.objects.active()
            .select_related()
            .prefetch_related(
                "items__track__work__author",
                "items__track__work__category",
                "items__track__work__genres",
                "items__track__work__moods",
                "items__track__narrator",
                "items__track__language",
                "items__track__album",
                "items__playlist__owner",
                "items__playlist__items__track",
                "items__album__author",
                "items__author",
                "items__narrator",
                "items__genre",
                "items__mood",
            )
            .order_by("sort_order", "identifier", "id")
        )
        if editorial_sections:
            return self.build_editorial_payload(editorial_sections)
        return self.build_default_payload()

    def build_editorial_payload(self, editorial_sections):
        hero = {
            "id": "hero",
            "title": "विशेष प्रस्तुति",
            "contentType": None,
            "content": None,
        }
        sections = []
        continue_index = 0
        continue_config = None
        for configured in editorial_sections:
            if configured.section_type == HomeSectionType.CONTINUE_LISTENING:
                continue_index = len(sections)
                continue_config = {
                    "id": configured.identifier,
                    "title": configured.title_ne,
                    "titleEnglish": configured.title_en,
                    "subtitle": configured.subtitle_ne,
                    "subtitleEnglish": configured.subtitle_en,
                    "sectionType": configured.section_type,
                    "layout": configured.layout,
                }
                continue
            items = [
                serialized
                for item in configured.items.all()
                if (serialized := self.serialize_editorial_item(item)) is not None
            ][: configured.max_items]
            if configured.section_type == HomeSectionType.HERO:
                if items:
                    content_type, content = items[0]
                    hero = {
                        "id": configured.identifier,
                        "title": configured.title_ne,
                        "titleEnglish": configured.title_en,
                        "subtitle": configured.subtitle_ne,
                        "subtitleEnglish": configured.subtitle_en,
                        "contentType": content_type,
                        "content": content,
                    }
                continue
            sections.append(
                {
                    "id": configured.identifier,
                    "title": configured.title_ne,
                    "titleEnglish": configured.title_en,
                    "subtitle": configured.subtitle_ne,
                    "subtitleEnglish": configured.subtitle_en,
                    "sectionType": configured.section_type,
                    "layout": configured.layout,
                    "items": [content for _, content in items],
                }
            )
        return {
            "hero": hero,
            "sections": sections,
            "_continueIndex": continue_index,
            "_continueSection": continue_config,
        }

    def serialize_editorial_item(self, item):
        now = timezone.now()
        if item.track_id:
            track = item.track
            if not (
                track.is_published
                and track.processing_status == TrackProcessingStatus.READY
                and track.published_at
                and track.published_at <= now
            ):
                return None
            return "track", CompactTrackSerializer(track).data
        if item.playlist_id:
            playlist = item.playlist
            if not (
                playlist.is_published
                and playlist.visibility == PlaylistVisibility.PUBLIC
            ):
                return None
            playable = [
                playlist_item.track
                for playlist_item in playlist.items.all()
                if (
                    playlist_item.track.is_published
                    and playlist_item.track.processing_status
                    == TrackProcessingStatus.READY
                    and playlist_item.track.published_at
                    and playlist_item.track.published_at <= now
                )
            ]
            playlist.trackCount = len(playable)
            playlist.totalDuration = sum(track.duration_seconds for track in playable)
            return "playlist", HomePlaylistSerializer(playlist).data
        if item.album_id:
            if not item.album.is_published:
                return None
            return "album", HomeAlbumSerializer(item.album).data
        if item.author_id:
            return "author", HomeAuthorSerializer(item.author).data
        if item.narrator_id:
            return "narrator", HomeNarratorSerializer(item.narrator).data
        if item.genre_id:
            if not item.genre.is_active:
                return None
            return "genre", HomeGenreSerializer(item.genre).data
        if item.mood_id:
            if not item.mood.is_active:
                return None
            item.mood.trackCount = 0
            return "mood", HomeMoodCollectionSerializer(item.mood).data
        return None

    def build_default_payload(self):
        playable = Q(
            items__track__is_published=True,
            items__track__processing_status=TrackProcessingStatus.READY,
            items__track__published_at__lte=timezone.now(),
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
                    "items__track__duration_seconds",
                    filter=playable,
                    default=0,
                ),
            )
            .order_by("-updated_at", "id")[:SECTION_LIMIT]
        )
        playlist_data = HomePlaylistSerializer(playlists, many=True).data

        tracks = public_track_queryset()
        trending = list(
            tracks.order_by("-play_count_cache", "-published_at", "id")[:SECTION_LIMIT]
        )
        recent = list(
            public_track_queryset().order_by("-published_at", "-created_at", "id")[
                :SECTION_LIMIT
            ]
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
            ).order_by("-is_featured", "-is_verified", "-popularity", "name_ne", "id")[
                :SECTION_LIMIT
            ]
        )
        narrators = list(
            Narrator.objects.order_by(
                "-is_featured",
                "-follower_count_cache",
                "-is_verified",
                "name_ne",
                "id",
            )[:SECTION_LIMIT]
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
            .order_by("sort_order", "name_ne", "id")[:MOOD_LIMIT]
        )
        albums = list(
            Album.objects.published()
            .filter(is_featured=True)
            .select_related("author")
            .order_by("-release_date", "-created_at", "id")[:SECTION_LIMIT]
        )
        trending_data = CompactTrackSerializer(trending, many=True).data
        recent_data = CompactTrackSerializer(recent, many=True).data
        album_data = HomeAlbumSerializer(albums, many=True).data
        hero_content = None
        hero_type = None
        if playlist_data:
            hero_content, hero_type = playlist_data[0], "playlist"
        elif trending_data:
            hero_content, hero_type = trending_data[0], "track"
        elif album_data:
            hero_content, hero_type = album_data[0], "album"

        return {
            "hero": {
                "id": "hero",
                "title": "विशेष प्रस्तुति",
                "contentType": hero_type,
                "content": hero_content,
            },
            "sections": [
                section(
                    "featured-playlists",
                    "विशेष प्लेलिस्टहरू",
                    playlist_data,
                    section_type=HomeSectionType.PLAYLISTS,
                ),
                section(
                    "trending-tracks",
                    "यो हप्ता लोकप्रिय",
                    trending_data,
                    section_type=HomeSectionType.TRACKS,
                ),
                section(
                    "recently-added",
                    "भर्खरै थपिएका",
                    recent_data,
                    section_type=HomeSectionType.TRACKS,
                ),
                section(
                    "popular-authors",
                    "लोकप्रिय लेखकहरू",
                    HomeAuthorSerializer(authors, many=True).data,
                    section_type=HomeSectionType.AUTHORS,
                ),
                section(
                    "popular-narrators",
                    "लोकप्रिय वाचकहरू",
                    HomeNarratorSerializer(narrators, many=True).data,
                    section_type=HomeSectionType.NARRATORS,
                ),
                section(
                    "mood-collections",
                    "मूडअनुसार सुन्नुहोस्",
                    HomeMoodCollectionSerializer(moods, many=True).data,
                    section_type=HomeSectionType.MOODS,
                    layout="grid",
                ),
                section(
                    "featured-albums",
                    "विशेष एल्बमहरू",
                    album_data,
                    section_type=HomeSectionType.ALBUMS,
                ),
            ],
        }

    def get_continue_section(self, user, *, configuration=None):
        progress = list(
            ListeningProgress.objects.filter(
                user=user,
                is_completed=False,
                position_seconds__gt=0,
                track_id__in=public_track_queryset().values("pk"),
            )
            .select_related(
                "track",
                "track__work",
                "track__work__author",
                "track__work__category",
                "track__album",
                "track__narrator",
                "track__language",
            )
            .prefetch_related("track__work__genres", "track__work__moods")
            .order_by("-last_listened_at", "-updated_at", "id")[:CONTINUE_LIMIT]
        )
        result = section(
            configuration["id"] if configuration else "continue-listening",
            configuration["title"] if configuration else "अहिले सुन्दै हुनुहुन्छ",
            ContinueListeningSerializer(progress, many=True).data,
            section_type=HomeSectionType.CONTINUE_LISTENING,
            layout=configuration["layout"] if configuration else "rail",
        )
        if configuration:
            result["titleEnglish"] = configuration["titleEnglish"]
            result["subtitle"] = configuration["subtitle"]
            result["subtitleEnglish"] = configuration["subtitleEnglish"]
        return result


home_service = HomeService()
