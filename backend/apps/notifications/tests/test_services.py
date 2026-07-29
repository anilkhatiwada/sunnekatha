from datetime import timedelta

import pytest
from django.utils import timezone

from apps.accounts.tests.factories import UserFactory
from apps.catalog.tests.factories import AudioTrackFactory
from apps.library.models import FollowedAuthor, FollowedNarrator, SavedPlaylist
from apps.notifications.models import Notification, NotificationType
from apps.notifications.services import notification_service
from apps.playlists.tests.factories import PlaylistFactory
from apps.uploads.models import UploadSession, UploadType

pytestmark = pytest.mark.django_db


def test_track_publication_notifies_author_and_narrator_followers_once():
    track = AudioTrackFactory()
    author_follower = UserFactory()
    narrator_follower = UserFactory()
    unrelated = UserFactory()
    FollowedAuthor.objects.create(user=author_follower, author=track.work.author)
    FollowedNarrator.objects.create(user=narrator_follower, narrator=track.narrator)

    notification_service.track_published(track)
    notification_service.track_published(track)

    assert (
        Notification.objects.filter(
            recipient=author_follower,
            notification_type=NotificationType.FOLLOWED_AUTHOR_PUBLISHED,
        ).count()
        == 1
    )
    assert (
        Notification.objects.filter(
            recipient=narrator_follower,
            notification_type=NotificationType.FOLLOWED_NARRATOR_PUBLISHED,
        ).count()
        == 1
    )
    assert not Notification.objects.filter(recipient=unrelated).exists()


def test_playlist_update_notifies_users_who_saved_it():
    playlist = PlaylistFactory()
    listener = UserFactory()
    SavedPlaylist.objects.create(user=listener, playlist=playlist)

    notification_service.playlist_updated(playlist)

    notification = Notification.objects.get(recipient=listener)
    assert notification.notification_type == NotificationType.PLAYLIST_UPDATED
    assert notification.data["playlistSlug"] == playlist.slug


def test_upload_processing_notifications_are_idempotent_per_outcome():
    creator = UserFactory(is_creator=True)
    upload = UploadSession.objects.create(
        user=creator,
        upload_type=UploadType.AUDIO_MASTER,
        object_key=f"temporary/uploads/audio-master/{creator.id}/recording.mp3",
        original_filename="recording.mp3",
        content_type="audio/mpeg",
        expected_size=1024,
        expires_at=timezone.now() + timedelta(minutes=10),
    )

    notification_service.upload_processing_completed(upload)
    notification_service.upload_processing_completed(upload)
    notification_service.upload_processing_failed(upload)
    notification_service.upload_processing_failed(upload)

    assert (
        Notification.objects.filter(
            recipient=creator,
            notification_type=NotificationType.UPLOAD_PROCESSING_COMPLETED,
        ).count()
        == 1
    )
    assert (
        Notification.objects.filter(
            recipient=creator,
            notification_type=NotificationType.UPLOAD_PROCESSING_FAILED,
        ).count()
        == 1
    )
