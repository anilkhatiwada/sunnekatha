from types import SimpleNamespace

import pytest
from django.contrib import admin
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from apps.accounts.models import User
from apps.accounts.tests.factories import UserFactory
from apps.authors.models import Author
from apps.authors.tests.factories import AuthorFactory
from apps.catalog.models import AudioTrack, CopyrightLicense, LiteraryWork
from apps.catalog.tests.factories import AudioTrackFactory, LiteraryWorkFactory
from apps.narrators.models import Narrator
from apps.narrators.tests.factories import NarratorFactory
from apps.playlists.models import Playlist
from apps.playlists.tests.factories import PlaylistFactory
from apps.uploads.models import UploadSession, UploadType

pytestmark = pytest.mark.django_db


def changelist_request(rf, model):
    request = rf.get(f"/admin/{model._meta.app_label}/{model._meta.model_name}/")
    request.user = UserFactory(is_staff=True, is_superuser=True)
    request.resolver_match = SimpleNamespace(
        url_name=f"{model._meta.app_label}_{model._meta.model_name}_changelist"
    )
    return request


def test_content_admin_lists_have_constant_query_counts(rf, django_assert_num_queries):
    AudioTrackFactory.create_batch(
        8,
        transcript="large transcript",
        waveform_data=[0.1, 0.4, 0.2],
    )
    PlaylistFactory.create_batch(8)
    AuthorFactory.create_batch(8, biography_ne="long biography")
    NarratorFactory.create_batch(8, biography_ne="long biography")

    track_admin = admin.site._registry[AudioTrack]
    track_request = changelist_request(rf, AudioTrack)
    with CaptureQueriesContext(connection) as captured:
        with django_assert_num_queries(1):
            tracks = list(track_admin.get_queryset(track_request))
            for track in tracks:
                track_admin.cover_thumbnail(track)
                track_admin.processing_indicator(track)
                track_admin.formatted_duration(track)
    track_sql = captured.captured_queries[0]["sql"].lower()
    assert '"transcript"' not in track_sql
    assert '"waveform_data"' not in track_sql
    assert '"audio_master_file"' not in track_sql

    playlist_admin = admin.site._registry[Playlist]
    playlist_request = changelist_request(rf, Playlist)
    with django_assert_num_queries(1):
        playlists = list(playlist_admin.get_queryset(playlist_request))
        for playlist in playlists:
            playlist_admin.track_count(playlist)
            playlist_admin.total_duration(playlist)

    author_admin = admin.site._registry[Author]
    author_request = changelist_request(rf, Author)
    with django_assert_num_queries(1):
        authors = list(author_admin.get_queryset(author_request))
        for author in authors:
            author_admin.work_count(author)
            author_admin.track_count(author)

    narrator_admin = admin.site._registry[Narrator]
    narrator_request = changelist_request(rf, Narrator)
    with django_assert_num_queries(1):
        narrators = list(narrator_admin.get_queryset(narrator_request))
        for narrator in narrators:
            narrator_admin.narrated_track_count(narrator)


def test_operational_admin_lists_have_bounded_queries(rf, django_assert_num_queries):
    LiteraryWorkFactory.create_batch(8, description_ne="long description")
    UserFactory.create_batch(8)
    work = LiteraryWorkFactory()
    CopyrightLicense.objects.create(
        literary_work=work,
        permission_type="audio",
    )
    uploader = UserFactory()
    for index in range(8):
        UploadSession.objects.create(
            user=uploader,
            upload_type=UploadType.AUDIO_MASTER,
            object_key=f"temporary/admin-performance-{index}.wav",
            original_filename=f"recording-{index}.wav",
            content_type="audio/wav",
            expected_size=100,
            expires_at=timezone.now(),
        )

    work_admin = admin.site._registry[LiteraryWork]
    work_request = changelist_request(rf, LiteraryWork)
    with django_assert_num_queries(1):
        works = list(work_admin.get_queryset(work_request))
        for item in works:
            work_admin.track_count(item)
            work_admin.publication_badge(item)

    user_admin = admin.site._registry[User]
    user_request = changelist_request(rf, User)
    with django_assert_num_queries(1):
        users = list(user_admin.get_queryset(user_request))
        for user in users:
            user_admin.premium_status(user)

    rights_admin = admin.site._registry[CopyrightLicense]
    rights_request = changelist_request(rf, CopyrightLicense)
    with django_assert_num_queries(1):
        licenses = list(rights_admin.get_queryset(rights_request))
        for license_record in licenses:
            rights_admin.copyright_status(license_record)
            rights_admin.document_availability(license_record)

    upload_admin = admin.site._registry[UploadSession]
    upload_request = changelist_request(rf, UploadSession)
    with CaptureQueriesContext(connection) as captured:
        with django_assert_num_queries(2):
            uploads = list(upload_admin.get_queryset(upload_request))
            for upload in uploads:
                upload_admin.processing_badge(upload)
                upload_admin.related_track_link(upload)
    upload_sql = "\n".join(query["sql"].lower() for query in captured.captured_queries)
    assert '"transcript"' not in upload_sql
    assert '"waveform_data"' not in upload_sql


def test_autocomplete_querysets_skip_aggregates_and_large_fields(
    rf, django_assert_num_queries
):
    AudioTrackFactory.create_batch(8, transcript="large", waveform_data=[0.2])
    track_admin = admin.site._registry[AudioTrack]
    request = rf.get(
        "/admin/autocomplete/",
        {"app_label": "playlists", "model_name": "playlistitem", "field_name": "track"},
    )
    request.user = UserFactory(is_staff=True, is_superuser=True)
    request.resolver_match = SimpleNamespace(url_name="autocomplete")

    with CaptureQueriesContext(connection) as captured:
        with django_assert_num_queries(1):
            tracks = list(track_admin.get_queryset(request))
            assert all(track.title_ne for track in tracks)

    sql = captured.captured_queries[0]["sql"].lower()
    assert " count(" not in sql
    assert '"transcript"' not in sql
    assert '"waveform_data"' not in sql
