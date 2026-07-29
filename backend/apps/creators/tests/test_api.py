from datetime import timedelta

import pytest
from django.contrib.auth.models import Permission
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.tests.factories import UserFactory
from apps.catalog.models import TrackReviewStatus
from apps.catalog.tests.factories import AudioTrackFactory
from apps.creators.models import (
    ContentContributor,
    CreatorProfile,
    CreatorRole,
    RightsLicenseAudit,
)
from apps.library.models import PlaybackSession
from apps.narrators.tests.factories import NarratorFactory
from apps.uploads.models import UploadSession, UploadType

pytestmark = pytest.mark.django_db


def client_for(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


def creator_with_profile(*, role=CreatorRole.CONTENT_UPLOADER):
    user = UserFactory(is_creator=True)
    profile = CreatorProfile.objects.create(
        user=user,
        display_name=user.display_name,
        roles=[role],
        is_approved=True,
    )
    return user, profile


def owned_draft(user=None, profile=None, role=CreatorRole.CONTENT_UPLOADER):
    track = AudioTrackFactory(is_published=False, published_at=None)
    if profile:
        ContentContributor.objects.create(track=track, creator=profile, role=role)
    elif user:
        track.narrator = NarratorFactory(user=user)
        track.save()
    return track


def test_creator_profile_is_owner_scoped_and_updateable():
    user, profile = creator_with_profile()

    response = client_for(user).patch(
        reverse("creators:profile"),
        {"displayName": "नयाँ नाम", "roles": ["editor", "rights_holder"]},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    profile.refresh_from_db()
    assert profile.display_name == "नयाँ नाम"
    assert profile.roles == ["editor", "rights_holder"]


def test_creator_track_lists_include_only_contributed_or_narrated_tracks():
    user, profile = creator_with_profile()
    contributed = owned_draft(profile=profile)
    narrated = owned_draft(user=user)
    AudioTrackFactory(is_published=False, published_at=None)

    response = client_for(user).get(reverse("creators:drafts"))

    assert response.data["count"] == 2
    assert {item["id"] for item in response.data["results"]} == {
        str(contributed.id),
        str(narrated.id),
    }


def test_creator_cannot_edit_another_creators_draft():
    owner, owner_profile = creator_with_profile()
    other, _ = creator_with_profile()
    track = owned_draft(profile=owner_profile)

    response = client_for(other).patch(
        reverse("creators:metadata", args=[track.slug]),
        {"titleNe": "चोरी गरिएको शीर्षक"},
        format="json",
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    track.refresh_from_db()
    assert track.title_ne != "चोरी गरिएको शीर्षक"


def test_creator_cannot_edit_published_fields_or_published_track():
    user, profile = creator_with_profile()
    track = AudioTrackFactory(is_published=True)
    ContentContributor.objects.create(
        track=track,
        creator=profile,
        role=CreatorRole.EDITOR,
    )

    response = client_for(user).patch(
        reverse("creators:metadata", args=[track.slug]),
        {"titleNe": "बदलिएको", "isPublished": False, "publishedAt": None},
        format="json",
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    track.refresh_from_db()
    assert track.is_published


def test_publication_and_processing_fields_are_rejected_on_draft():
    user, profile = creator_with_profile()
    track = owned_draft(profile=profile)

    response = client_for(user).patch(
        reverse("creators:metadata", args=[track.slug]),
        {"isPublished": True, "processingStatus": "ready"},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert {"isPublished", "processingStatus"} <= response.data["errors"].keys()
    track.refresh_from_db()
    assert not track.is_published


def test_only_rights_holder_can_change_rights_and_change_is_audited():
    user, profile = creator_with_profile(role=CreatorRole.RIGHTS_HOLDER)
    track = owned_draft(profile=profile, role=CreatorRole.RIGHTS_HOLDER)

    response = client_for(user).patch(
        reverse("creators:metadata", args=[track.slug]),
        {
            "copyrightStatus": "licensed",
            "copyrightOwner": "SunneKatha परीक्षण",
            "licenseNotes": "अनुमति अभिलेख",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    track.work.refresh_from_db()
    assert track.work.copyright_status == "licensed"
    audit = RightsLicenseAudit.objects.get(track=track)
    assert audit.actor == user
    assert audit.changes["copyrightOwner"]["to"] == "SunneKatha परीक्षण"


def test_non_rights_contributor_cannot_change_license_fields():
    user, profile = creator_with_profile(role=CreatorRole.EDITOR)
    track = owned_draft(profile=profile, role=CreatorRole.EDITOR)

    response = client_for(user).patch(
        reverse("creators:metadata", args=[track.slug]),
        {"licenseNotes": "unauthorized"},
        format="json",
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert not RightsLicenseAudit.objects.filter(track=track).exists()


def test_creator_submits_ready_draft_but_cannot_publish_it():
    user, profile = creator_with_profile()
    track = owned_draft(profile=profile)

    submitted = client_for(user).post(reverse("creators:submit", args=[track.slug]))
    publish = client_for(user).post(reverse("creators:approve", args=[track.slug]))

    assert submitted.status_code == status.HTTP_200_OK
    assert submitted.data["reviewStatus"] == TrackReviewStatus.SUBMITTED
    assert publish.status_code == status.HTTP_403_FORBIDDEN
    track.refresh_from_db()
    assert not track.is_published


def test_authorized_editor_publisher_can_approve_and_publish_submitted_track():
    creator, profile = creator_with_profile()
    track = owned_draft(profile=profile)
    client_for(creator).post(reverse("creators:submit", args=[track.slug]))
    staff = UserFactory(is_staff=True)
    staff.user_permissions.add(
        *Permission.objects.filter(
            content_type__app_label="catalog",
            codename__in=("approve_audiotrack", "publish_audiotrack"),
        )
    )
    staff = staff.__class__.objects.get(pk=staff.pk)

    response = client_for(staff).post(reverse("creators:approve", args=[track.slug]))

    assert response.status_code == status.HTTP_200_OK
    track.refresh_from_db()
    assert track.is_published
    assert track.review_status == TrackReviewStatus.PUBLISHED
    assert track.reviewed_by == staff


def test_creator_upload_sessions_are_owner_scoped():
    user, _ = creator_with_profile()
    own = UploadSession.objects.create(
        user=user,
        upload_type=UploadType.AUDIO_MASTER,
        object_key="temporary/uploads/own.mp3",
        original_filename="own.mp3",
        content_type="audio/mpeg",
        expected_size=100,
        expires_at=timezone.now() + timedelta(minutes=5),
    )
    UploadSession.objects.create(
        user=UserFactory(is_creator=True),
        upload_type=UploadType.AUDIO_MASTER,
        object_key="temporary/uploads/other.mp3",
        original_filename="other.mp3",
        content_type="audio/mpeg",
        expected_size=100,
        expires_at=timezone.now() + timedelta(minutes=5),
    )

    response = client_for(user).get(reverse("creators:uploads"))

    assert response.data["count"] == 1
    assert response.data["results"][0]["id"] == str(own.id)


def test_creator_can_view_basic_owned_track_analytics():
    user, profile = creator_with_profile()
    track = owned_draft(profile=profile)
    track.play_count_cache = 12
    track.save(update_fields=("play_count_cache", "updated_at"))
    PlaybackSession.objects.create(
        user=UserFactory(),
        track=track,
        device_id="creator-analytics-test",
        listened_seconds=30,
        completed=True,
    )

    response = client_for(user).get(reverse("creators:analytics", args=[track.slug]))

    assert response.status_code == status.HTTP_200_OK
    assert response.data["playCount"] == 12
    assert response.data["playbackSessions"] == 1
    assert response.data["completedSessions"] == 1
