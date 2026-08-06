from datetime import date, timedelta
from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.authors.models import Author
from apps.catalog.models import (
    Album,
    AlbumType,
    AudioTrack,
    CopyrightStatus,
    LiteraryWork,
    TrackProcessingStatus,
    TrackReviewStatus,
)
from apps.creators.models import CreatorProfile, CreatorRole
from apps.home.models import HomeSection, HomeSectionItem, HomeSectionType
from apps.library.models import (
    FavoriteTrack,
    FollowedAuthor,
    FollowedNarrator,
    ListeningProgress,
    SavedPlaylist,
)
from apps.narrators.models import Narrator
from apps.playlists.models import (
    Playlist,
    PlaylistItem,
    PlaylistType,
    PlaylistVisibility,
)
from apps.subscriptions.models import (
    PlanAccessLevel,
    SubscriptionPlan,
    SubscriptionStatus,
    UserSubscription,
)
from apps.taxonomy.management.commands.seed_taxonomies import SEED_GROUPS
from apps.taxonomy.models import ContentCategory, Genre, Language, Mood

DEMO_PASSWORD = "SunneKathaDemo!2026"
DEMO_EMAILS = (
    "listener@sunnekatha.local",
    "premium@sunnekatha.local",
    "creator@sunnekatha.local",
    "editor@sunnekatha.local",
)
DEMO_AUTHOR_SLUGS = ("anupama-karki", "dipen-rai", "maya-tamang")
DEMO_NARRATOR_SLUGS = ("aarati-gurung", "nischal-thapa")
DEMO_WORK_SLUGS = (
    "pahadko-bato",
    "jhyalma-pareko-jun",
    "sano-biu",
    "pharkine-chara",
)
DEMO_ALBUM_SLUGS = ("sanjhka-kathaharu", "manaka-laharharu")
DEMO_TRACK_SLUGS = (
    "pahadko-bato-1",
    "jhyalma-pareko-jun",
    "sano-biu",
    "pharkine-chara",
    "badalpachhiko-gham",
    "nadi-ko-geet",
)
DEMO_PLAYLIST_SLUGS = ("sanjhko-sunai", "shanta-man")
DEMO_SECTION_IDS = (
    "demo-hero",
    "demo-featured-playlists",
    "demo-trending-tracks",
    "demo-featured-authors",
    "demo-featured-narrators",
    "demo-moods",
    "demo-featured-albums",
)


class Command(BaseCommand):
    help = "Create idempotent, fictional SunneKatha demo content for development."

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear-existing-data",
            action="store_true",
            help=(
                "Delete only records owned by this command's fixed demo identifiers "
                "before rebuilding them. Unrelated development data is preserved."
            ),
        )

    @transaction.atomic
    def handle(self, *args, **options):
        del args
        if not settings.DEBUG:
            raise CommandError(
                "seed_demo_data is development-only and requires DEBUG=True."
            )
        if options["clear_existing_data"]:
            self._clear_demo_data()

        self._seed_taxonomies()
        users = self._seed_users()
        authors = self._seed_authors()
        narrators = self._seed_narrators(users)
        genres = {item.slug: item for item in Genre.objects.all()}
        moods = {item.slug: item for item in Mood.objects.all()}
        language = Language.objects.get(slug="ne")
        works = self._seed_works(authors, language, genres, moods)
        albums = self._seed_albums(authors, genres, moods)
        tracks = self._seed_tracks(works, albums, narrators, language)
        playlists = self._seed_playlists(tracks)
        self._seed_library(users, authors, narrators, tracks, playlists)
        self._seed_subscription(users)
        self._seed_home(authors, narrators, moods, albums, tracks, playlists)

        self.stdout.write(self.style.SUCCESS("SunneKatha demo data is ready."))
        self.stdout.write("Development-only credentials (all use the same password):")
        for email in DEMO_EMAILS:
            self.stdout.write(f"  {email} / {DEMO_PASSWORD}")
        self.stdout.write(
            self.style.WARNING(
                "These credentials are intentionally public and must never be used "
                "outside local development."
            )
        )

    def _clear_demo_data(self):
        HomeSection.objects.filter(identifier__in=DEMO_SECTION_IDS).delete()
        Playlist.objects.filter(slug__in=DEMO_PLAYLIST_SLUGS).delete()
        AudioTrack.objects.filter(slug__in=DEMO_TRACK_SLUGS).delete()
        Album.objects.filter(slug__in=DEMO_ALBUM_SLUGS).delete()
        LiteraryWork.objects.filter(slug__in=DEMO_WORK_SLUGS).delete()
        Narrator.objects.filter(slug__in=DEMO_NARRATOR_SLUGS).delete()
        Author.objects.filter(slug__in=DEMO_AUTHOR_SLUGS).delete()
        User.objects.filter(email__in=DEMO_EMAILS).delete()
        self.stdout.write("Existing command-owned demo records cleared.")

    @staticmethod
    def _seed_taxonomies():
        for model, records in SEED_GROUPS:
            for sort_order, (slug, name_ne, name_en, description) in enumerate(records):
                model.objects.update_or_create(
                    slug=slug,
                    defaults={
                        "name_ne": name_ne,
                        "name_en": name_en,
                        "description": description,
                        "sort_order": sort_order,
                        "is_active": True,
                    },
                )

    @staticmethod
    def _seed_users():
        records = (
            (
                "listener@sunnekatha.local",
                "demo_listener",
                "कथा प्रेमी",
                {"is_creator": False},
            ),
            (
                "premium@sunnekatha.local",
                "demo_premium",
                "प्रिमियम श्रोता",
                {"is_creator": False},
            ),
            (
                "creator@sunnekatha.local",
                "demo_creator",
                "आरती गुरुङ",
                {"is_creator": True},
            ),
            (
                "editor@sunnekatha.local",
                "demo_editor",
                "सम्पादक",
                {"is_creator": True, "is_staff": True},
            ),
        )
        users = {}
        for email, username, display_name, flags in records:
            user, _ = User.objects.update_or_create(
                email=email,
                defaults={
                    "username": username,
                    "display_name": display_name,
                    "is_active": True,
                    "is_staff": False,
                    "is_superuser": False,
                    **flags,
                },
            )
            user.set_password(DEMO_PASSWORD)
            user.save(update_fields=("password", "updated_at"))
            users[email] = user

        CreatorProfile.objects.update_or_create(
            user=users["creator@sunnekatha.local"],
            defaults={
                "display_name": "आरती गुरुङ",
                "biography": "कथा र कवितालाई आत्मीय स्वरमा प्रस्तुत गर्ने वाचक।",
                "roles": [CreatorRole.NARRATOR, CreatorRole.CONTENT_UPLOADER],
                "is_approved": True,
            },
        )
        CreatorProfile.objects.update_or_create(
            user=users["editor@sunnekatha.local"],
            defaults={
                "display_name": "SunneKatha सम्पादक",
                "biography": "स्थानीय विकासका लागि डेमो सम्पादक।",
                "roles": [CreatorRole.EDITOR],
                "is_approved": True,
            },
        )
        return users

    @staticmethod
    def _seed_authors():
        records = (
            (
                "anupama-karki",
                "अनुपमा कार्की",
                "Anupama Karki",
                "पहाड, स्मृति र दैनिक जीवनका सूक्ष्म कथा लेख्ने समकालीन स्रष्टा।",
            ),
            (
                "dipen-rai",
                "दीपेन राई",
                "Dipen Rai",
                "प्रकृति र यात्रालाई सरल भाषामा उतार्ने कथाकार तथा निबन्धकार।",
            ),
            (
                "maya-tamang",
                "माया तामाङ",
                "Maya Tamang",
                "बालमन, लोकलय र आशाका मौलिक रचना सिर्जना गर्ने लेखक।",
            ),
        )
        authors = {}
        for slug, name_ne, name_en, biography in records:
            author, _ = Author.objects.update_or_create(
                slug=slug,
                defaults={
                    "name_ne": name_ne,
                    "name_en": name_en,
                    "biography_ne": biography,
                    "country": "Nepal",
                    "is_featured": True,
                    "is_verified": True,
                },
            )
            authors[slug] = author
        return authors

    @staticmethod
    def _seed_narrators(users):
        records = (
            (
                "aarati-gurung",
                users["creator@sunnekatha.local"],
                "आरती गुरुङ",
                "Aarati Gurung",
            ),
            ("nischal-thapa", None, "निश्चल थापा", "Nischal Thapa"),
        )
        narrators = {}
        for slug, user, name_ne, name_en in records:
            narrator, _ = Narrator.objects.update_or_create(
                slug=slug,
                defaults={
                    "user": user,
                    "name_ne": name_ne,
                    "name_en": name_en,
                    "biography_ne": "मौलिक नेपाली साहित्यका अनुभवी स्वर कलाकार।",
                    "is_featured": True,
                    "is_verified": True,
                    "follower_count_cache": 1250 if user else 830,
                },
            )
            narrators[slug] = narrator
        return narrators

    @staticmethod
    def _seed_works(authors, language, genres, moods):
        records = (
            (
                "pahadko-bato",
                "पहाडको बाटो",
                "The Mountain Path",
                "story",
                "anupama-karki",
                ("short-story",),
                ("inspiration",),
            ),
            (
                "jhyalma-pareko-jun",
                "झ्यालमा परेको जून",
                "Moonlight at the Window",
                "poem",
                "dipen-rai",
                ("poetry",),
                ("calm", "longing"),
            ),
            (
                "sano-biu",
                "सानो बिउ",
                "The Little Seed",
                "folk-tale",
                "maya-tamang",
                ("folk-tale", "children"),
                ("inspiration",),
            ),
            (
                "pharkine-chara",
                "फर्किने चरा",
                "The Returning Bird",
                "essay",
                "anupama-karki",
                ("essay",),
                ("longing",),
            ),
        )
        works = {}
        now = timezone.now()
        for (
            slug,
            title_ne,
            title_en,
            category_slug,
            author_slug,
            genre_slugs,
            mood_slugs,
        ) in records:
            work, _ = LiteraryWork.objects.update_or_create(
                slug=slug,
                defaults={
                    "title_ne": title_ne,
                    "title_en": title_en,
                    "description_ne": (
                        "SunneKatha का लागि तयार गरिएको पूर्णतः मौलिक डेमो रचना।"
                    ),
                    "category": ContentCategory.objects.get(slug=category_slug),
                    "author": authors[author_slug],
                    "language": language,
                    "publication_year": date.today().year,
                    "copyright_status": CopyrightStatus.PERMISSION_GRANTED,
                    "copyright_owner": "SunneKatha Demo",
                    "license_notes": (
                        "Development demo only; no audio file is included."
                    ),
                    "is_featured": True,
                    "is_published": True,
                    "published_at": now,
                },
            )
            work.genres.set(genres[item] for item in genre_slugs)
            work.moods.set(moods[item] for item in mood_slugs)
            works[slug] = work
        return works

    @staticmethod
    def _seed_albums(authors, genres, moods):
        records = (
            (
                "sanjhka-kathaharu",
                "साँझका कथाहरू",
                "Stories for the Evening",
                "anupama-karki",
                "short-story",
                "calm",
            ),
            (
                "manaka-laharharu",
                "मनका लहरहरू",
                "Waves of the Heart",
                "dipen-rai",
                "poetry",
                "longing",
            ),
        )
        albums = {}
        for slug, title_ne, title_en, author_slug, genre_slug, mood_slug in records:
            album, _ = Album.objects.update_or_create(
                slug=slug,
                defaults={
                    "title_ne": title_ne,
                    "title_en": title_en,
                    "description_ne": "मौलिक डेमो श्रव्य रचनाहरूको सङ्ग्रह।",
                    "author": authors[author_slug],
                    "album_type": AlbumType.COLLECTION,
                    "release_date": date.today(),
                    "is_featured": True,
                    "is_published": True,
                },
            )
            album.genres.set([genres[genre_slug]])
            album.moods.set([moods[mood_slug]])
            albums[slug] = album
        return albums

    @staticmethod
    def _seed_tracks(works, albums, narrators, language):
        records = (
            (
                "pahadko-bato-1",
                "पहाडको बाटो",
                "pahadko-bato",
                "sanjhka-kathaharu",
                "aarati-gurung",
                742,
                True,
                False,
            ),
            (
                "jhyalma-pareko-jun",
                "झ्यालमा परेको जून",
                "jhyalma-pareko-jun",
                "manaka-laharharu",
                "nischal-thapa",
                286,
                True,
                False,
            ),
            (
                "sano-biu",
                "सानो बिउ",
                "sano-biu",
                None,
                "aarati-gurung",
                518,
                True,
                False,
            ),
            (
                "pharkine-chara",
                "फर्किने चरा",
                "pharkine-chara",
                None,
                "nischal-thapa",
                630,
                False,
                True,
            ),
            (
                "badalpachhiko-gham",
                "बादलपछिको घाम",
                "pahadko-bato",
                "sanjhka-kathaharu",
                "aarati-gurung",
                455,
                False,
                False,
            ),
            (
                "nadi-ko-geet",
                "नदीको गीत",
                "jhyalma-pareko-jun",
                "manaka-laharharu",
                "nischal-thapa",
                334,
                False,
                False,
            ),
        )
        tracks = {}
        now = timezone.now()
        for index, (
            slug,
            title,
            work_slug,
            album_slug,
            narrator_slug,
            duration,
            featured,
            premium,
        ) in enumerate(records, start=1):
            track, _ = AudioTrack.objects.update_or_create(
                slug=slug,
                defaults={
                    "work": works[work_slug],
                    "album": albums.get(album_slug),
                    "track_number": index,
                    "title_ne": title,
                    "title_en": slug.replace("-", " ").title(),
                    "description_ne": (
                        "यो मौलिक विकास डेमो हो। कुनै प्रतिलिपि अधिकारयुक्त "
                        "अडियो समावेश गरिएको छैन।"
                    ),
                    "narrator": narrators[narrator_slug],
                    "language": language,
                    "duration_seconds": duration,
                    "waveform_data": [12, 25, 42, 31, 58, 44, 27, 18],
                    "is_premium": premium,
                    "is_featured": featured,
                    "is_published": True,
                    "processing_status": TrackProcessingStatus.READY,
                    "review_status": TrackReviewStatus.APPROVED,
                    "published_at": now - timedelta(days=index),
                    "play_count_cache": 1800 - index * 137,
                },
            )
            tracks[slug] = track
        return tracks

    @staticmethod
    def _seed_playlists(tracks):
        records = (
            (
                "sanjhko-sunai",
                "साँझको सुनाइ",
                "Evening Listening",
                ("pahadko-bato-1", "jhyalma-pareko-jun", "pharkine-chara"),
            ),
            (
                "shanta-man",
                "शान्त मन",
                "A Calm Mind",
                ("nadi-ko-geet", "sano-biu", "jhyalma-pareko-jun"),
            ),
        )
        playlists = {}
        for slug, title_ne, title_en, track_slugs in records:
            playlist, _ = Playlist.objects.update_or_create(
                slug=slug,
                defaults={
                    "owner": None,
                    "title_ne": title_ne,
                    "title_en": title_en,
                    "description_ne": "सम्पादकीय रूपमा छानिएका मौलिक डेमो रचना।",
                    "playlist_type": PlaylistType.EDITORIAL,
                    "visibility": PlaylistVisibility.PUBLIC,
                    "is_featured": True,
                    "is_published": True,
                },
            )
            PlaylistItem.objects.filter(playlist=playlist).delete()
            PlaylistItem.objects.bulk_create(
                [
                    PlaylistItem(
                        playlist=playlist,
                        track=tracks[track_slug],
                        position=position,
                    )
                    for position, track_slug in enumerate(track_slugs, start=1)
                ]
            )
            playlists[slug] = playlist
        return playlists

    @staticmethod
    def _seed_library(users, authors, narrators, tracks, playlists):
        listener = users["listener@sunnekatha.local"]
        for slug in ("pahadko-bato-1", "sano-biu"):
            FavoriteTrack.objects.get_or_create(user=listener, track=tracks[slug])
        SavedPlaylist.objects.get_or_create(
            user=listener,
            playlist=playlists["sanjhko-sunai"],
        )
        FollowedAuthor.objects.get_or_create(
            user=listener,
            author=authors["anupama-karki"],
        )
        FollowedNarrator.objects.get_or_create(
            user=listener,
            narrator=narrators["aarati-gurung"],
        )
        ListeningProgress.objects.update_or_create(
            user=listener,
            track=tracks["pahadko-bato-1"],
            defaults={
                "position_seconds": Decimal("215"),
                "duration_seconds": Decimal("742"),
                "progress_percentage": Decimal("28.98"),
                "is_completed": False,
                "last_listened_at": timezone.now(),
            },
        )

    @staticmethod
    def _seed_subscription(users):
        plan, _ = SubscriptionPlan.objects.update_or_create(
            slug="demo-premium",
            defaults={
                "name": "Demo Premium",
                "description": "Development-only premium access.",
                "access_level": PlanAccessLevel.PREMIUM,
                "allows_premium_streaming": True,
                "allows_downloads": False,
                "is_active": True,
                "sort_order": 10,
            },
        )
        UserSubscription.objects.update_or_create(
            user=users["premium@sunnekatha.local"],
            status=SubscriptionStatus.ACTIVE,
            defaults={
                "plan": plan,
                "starts_at": timezone.now(),
                "ends_at": timezone.now() + timedelta(days=30),
            },
        )

    @staticmethod
    def _seed_home(authors, narrators, moods, albums, tracks, playlists):
        sections = (
            (
                "demo-hero",
                "आजको विशेष",
                "Today's Feature",
                HomeSectionType.HERO,
                [("track", tracks["pahadko-bato-1"])],
            ),
            (
                "demo-featured-playlists",
                "सम्पादकको छनोट",
                "Editor's Picks",
                HomeSectionType.PLAYLISTS,
                [("playlist", value) for value in playlists.values()],
            ),
            (
                "demo-trending-tracks",
                "लोकप्रिय सुनाइ",
                "Trending",
                HomeSectionType.TRACKS,
                [("track", value) for value in tracks.values()],
            ),
            (
                "demo-featured-authors",
                "प्रिय लेखक",
                "Featured Authors",
                HomeSectionType.AUTHORS,
                [("author", value) for value in authors.values()],
            ),
            (
                "demo-featured-narrators",
                "लोकप्रिय वाचक",
                "Featured Narrators",
                HomeSectionType.NARRATORS,
                [("narrator", value) for value in narrators.values()],
            ),
            (
                "demo-moods",
                "मनको भाव",
                "Browse by Mood",
                HomeSectionType.MOODS,
                [
                    ("mood", moods["calm"]),
                    ("mood", moods["inspiration"]),
                    ("mood", moods["longing"]),
                ],
            ),
            (
                "demo-featured-albums",
                "विशेष सङ्ग्रह",
                "Featured Albums",
                HomeSectionType.ALBUMS,
                [("album", value) for value in albums.values()],
            ),
        )
        for sort_order, (
            identifier,
            title_ne,
            title_en,
            section_type,
            items,
        ) in enumerate(sections):
            section, _ = HomeSection.objects.update_or_create(
                identifier=identifier,
                defaults={
                    "title_ne": title_ne,
                    "title_en": title_en,
                    "section_type": section_type,
                    "sort_order": sort_order,
                    "is_active": True,
                },
            )
            HomeSectionItem.objects.filter(section=section).delete()
            HomeSectionItem.objects.bulk_create(
                [
                    HomeSectionItem(
                        section=section,
                        position=position,
                        **{target_type: target},
                    )
                    for position, (target_type, target) in enumerate(items, start=1)
                ]
            )
