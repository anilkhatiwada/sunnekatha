from datetime import timedelta
from unittest.mock import Mock

import pytest
from django.contrib import admin
from django.contrib.auth.models import Permission
from django.urls import reverse
from django.utils import timezone

from apps.accounts.tests.factories import UserFactory
from apps.catalog.tests.factories import AudioTrackFactory
from apps.narrators.admin import (
    HasPublishedTracksFilter,
    LinkedAccountFilter,
    NarratorAdmin,
)
from apps.narrators.models import Narrator
from apps.narrators.tests.factories import NarratorFactory

pytestmark = pytest.mark.django_db


def test_narrator_admin_configuration_matches_editorial_workflow():
    model_admin = admin.site._registry[Narrator]

    assert isinstance(model_admin, NarratorAdmin)
    assert model_admin.list_display == (
        "image_thumbnail",
        "name_ne",
        "name_en",
        "user",
        "narrated_track_count",
        "follower_count_cache",
        "is_featured",
        "is_verified",
        "created_at",
    )
    assert LinkedAccountFilter in model_admin.list_filter
    assert HasPublishedTracksFilter in model_admin.list_filter
    assert "recent_narration_preview" in model_admin.readonly_fields
    assert "verify_selected" in model_admin.actions
    assert tuple(name for name, _ in model_admin.fieldsets) == (
        "Identity",
        "Biography",
        "Profile Image",
        "Linked Account",
        "Editorial Status",
        "Narrated Content",
        "Statistics",
        "System Information",
    )


def test_narrator_admin_annotates_track_count_without_row_queries(rf):
    narrator = NarratorFactory()
    AudioTrackFactory.create_batch(2, narrator=narrator)
    model_admin = admin.site._registry[Narrator]
    request = rf.get("/")
    request.user = UserFactory(is_staff=True, is_superuser=True)

    result = model_admin.get_queryset(request).get(pk=narrator.pk)

    assert model_admin.narrated_track_count(result) == 2


def test_narrator_admin_filters_linked_accounts_and_published_tracks(client):
    user = UserFactory(is_staff=True, is_superuser=True)
    linked_user = UserFactory()
    expected = NarratorFactory(user=linked_user)
    AudioTrackFactory(narrator=expected)
    NarratorFactory(user=None)
    client.force_login(user)

    response = client.get(
        reverse("admin:narrators_narrator_changelist"),
        {"linked_account": "yes", "has_published_tracks": "yes"},
    )

    assert response.status_code == 200
    assert list(response.context["cl"].result_list) == [expected]


def test_narrator_admin_related_and_public_links_use_named_routes():
    narrator = NarratorFactory()
    AudioTrackFactory(narrator=narrator)
    model_admin = admin.site._registry[Narrator]

    related = str(model_admin.related_tracks_link(narrator))
    preview = str(model_admin.public_profile_preview(narrator))

    assert reverse("admin:catalog_audiotrack_changelist") in related
    assert reverse("narrators:detail", kwargs={"slug": narrator.slug}) in preview


def test_recent_narration_widget_is_lazy_and_uses_newest_published_track(
    client, monkeypatch
):
    user = UserFactory(is_staff=True, is_superuser=True)
    narrator = NarratorFactory()
    older = AudioTrackFactory(
        narrator=narrator,
        published_at=timezone.now() - timedelta(days=2),
        stream_file_low="processed/audio/older-low.mp3",
    )
    newest = AudioTrackFactory(
        narrator=narrator,
        published_at=timezone.now() - timedelta(days=1),
        stream_file_high="processed/audio/newest-high.mp3",
    )
    deliver = Mock()
    monkeypatch.setattr(
        "apps.narrators.admin.cloudfront_media_service.deliver",
        deliver,
    )
    client.force_login(user)

    response = client.get(
        reverse("admin:narrators_narrator_change", args=(narrator.pk,))
    )

    assert response.status_code == 200
    assert newest.title_ne.encode() in response.content
    assert older.title_ne.encode() not in response.content
    deliver.assert_not_called()


def test_recent_narration_delivery_requires_track_permission(client):
    narrator = NarratorFactory()
    AudioTrackFactory(
        narrator=narrator,
        stream_file_low="processed/audio/recent-low.mp3",
    )
    editor = UserFactory(is_staff=True)
    editor.user_permissions.add(
        Permission.objects.get(
            content_type__app_label="narrators",
            codename="view_narrator",
        )
    )
    client.force_login(editor)

    response = client.get(
        reverse(
            "admin:narrators_narrator_audio_delivery",
            kwargs={"object_id": narrator.pk, "quality": "low"},
        )
    )

    assert response.status_code == 403
    assert response["Cache-Control"].startswith("private, no-store")


def test_verify_action_updates_selected_narrators(client):
    user = UserFactory(is_staff=True, is_superuser=True)
    narrator = NarratorFactory(is_verified=False)
    client.force_login(user)

    response = client.post(
        reverse("admin:narrators_narrator_changelist"),
        {
            "action": "verify_selected",
            "_selected_action": str(narrator.pk),
        },
    )

    assert response.status_code == 302
    narrator.refresh_from_db()
    assert narrator.is_verified is True
