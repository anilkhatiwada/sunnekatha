import pytest
from django.contrib import admin
from django.utils import timezone

from apps.accounts.tests.factories import UserFactory
from apps.authors.models import Author
from apps.authors.tests.factories import AuthorFactory
from apps.catalog.models import AudioTrack, CopyrightLicense, LiteraryWork
from apps.catalog.tests.factories import AudioTrackFactory
from apps.narrators.models import Narrator
from apps.playlists.models import Playlist, PlaylistItem
from apps.search.models import SearchAlias, SearchEntityType
from apps.uploads.models import UploadSession, UploadType

pytestmark = pytest.mark.django_db


def request_for(rf):
    request = rf.get("/admin/", {"q": "search"})
    request.user = UserFactory(is_staff=True, is_superuser=True)
    return request


@pytest.mark.parametrize(
    "field,value",
    [("name_ne", "भानुभक्त"), ("name_en", "Bhanubhakta")],
)
def test_author_admin_searches_nepali_and_english(rf, field, value):
    author = AuthorFactory(**{field: value})
    model_admin = admin.site._registry[Author]

    results, _ = model_admin.get_search_results(
        request_for(rf), model_admin.get_queryset(request_for(rf)), value
    )

    assert results.filter(pk=author.pk).exists()


def test_author_admin_searches_romanized_alias(rf):
    author = AuthorFactory(name_ne="लेखक")
    SearchAlias.objects.create(
        entity_type=SearchEntityType.AUTHOR,
        object_id=author.pk,
        alias="Mahakavi Lekhak",
    )
    model_admin = admin.site._registry[Author]
    request = request_for(rf)

    results, duplicates = model_admin.get_search_results(
        request, model_admin.get_queryset(request), "mahakavi lekh"
    )

    assert results.filter(pk=author.pk).exists()
    assert duplicates is True


def test_track_admin_searches_related_romanized_author_and_exact_id(rf):
    track = AudioTrackFactory()
    SearchAlias.objects.create(
        entity_type=SearchEntityType.AUTHOR,
        object_id=track.work.author_id,
        alias="Kavi Shiromani",
    )
    model_admin = admin.site._registry[AudioTrack]
    request = request_for(rf)
    queryset = model_admin.get_queryset(request)

    alias_results, _ = model_admin.get_search_results(
        request, queryset, "Kavi Shiromani"
    )
    id_results, _ = model_admin.get_search_results(request, queryset, str(track.pk))

    assert alias_results.filter(pk=track.pk).exists()
    assert id_results.filter(pk=track.pk).exists()


def test_upload_admin_searches_original_filename(rf):
    upload = UploadSession.objects.create(
        user=UserFactory(),
        upload_type=UploadType.AUDIO_MASTER,
        object_key="temporary/search-test.wav",
        original_filename="nepali-poem-master.wav",
        content_type="audio/wav",
        expected_size=100,
        expires_at=timezone.now(),
    )
    model_admin = admin.site._registry[UploadSession]
    request = request_for(rf)

    results, _ = model_admin.get_search_results(
        request, model_admin.get_queryset(request), "poem-master"
    )

    assert results.filter(pk=upload.pk).exists()


def test_large_relationships_use_autocomplete_widgets():
    assert {"author", "language"} <= set(
        admin.site._registry[LiteraryWork].autocomplete_fields
    )
    assert {"work", "album", "narrator", "language"} <= set(
        admin.site._registry[AudioTrack].autocomplete_fields
    )
    assert {"literary_work", "rights_holder"} <= set(
        admin.site._registry[CopyrightLicense].autocomplete_fields
    )
    assert "user" in admin.site._registry[Narrator].autocomplete_fields
    assert "owner" in admin.site._registry[Playlist].autocomplete_fields
    assert {"playlist", "track"} <= set(
        admin.site._registry[PlaylistItem].autocomplete_fields
    )
