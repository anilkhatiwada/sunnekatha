import pytest
from django.contrib.auth.models import Permission
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.accounts.tests.factories import UserFactory
from apps.catalog.models import TrackProcessingStatus
from apps.common.models import AdministrativeAudit, AdministrativeAuditAction
from apps.playlists.services import playlist_item_service
from apps.playlists.tests.factories import PlaylistFactory, PlaylistItemFactory

pytestmark = pytest.mark.django_db


def test_playlist_service_rejects_non_owner_without_staff_permission():
    playlist = PlaylistFactory()
    item = PlaylistItemFactory(playlist=playlist)

    with pytest.raises(PermissionDenied):
        playlist_item_service.remove(
            playlist=playlist,
            track=item.track,
            actor=UserFactory(),
        )


def test_reorder_records_staff_actor_and_compact_order_summary():
    actor = UserFactory(is_staff=True)
    playlist = PlaylistFactory(owner=actor)
    first = PlaylistItemFactory(playlist=playlist, position=1)
    second = PlaylistItemFactory(playlist=playlist, position=2)

    playlist_item_service.reorder(
        playlist=playlist,
        track_ids=[second.track_id, first.track_id],
        actor=actor,
    )

    audit = AdministrativeAudit.objects.get(
        action=AdministrativeAuditAction.PLAYLIST_REORDERED,
        object_id=str(playlist.pk),
    )
    assert audit.staff_user == actor
    assert "position" in audit.before_summary
    assert "position" in audit.after_summary


def test_safe_publish_skips_empty_and_unavailable_playlists():
    actor = UserFactory(is_staff=True)
    actor.user_permissions.add(
        Permission.objects.get(
            content_type__app_label="playlists",
            codename="change_playlist",
        )
    )
    ready = PlaylistFactory(is_published=False)
    PlaylistItemFactory(playlist=ready, position=1)
    unavailable = PlaylistFactory(is_published=False)
    PlaylistItemFactory(
        playlist=unavailable,
        position=1,
        track__is_published=False,
        track__published_at=None,
        track__processing_status=TrackProcessingStatus.PROCESSING,
    )
    empty = PlaylistFactory(is_published=False)
    queryset = ready.__class__.objects.filter(
        pk__in=(ready.pk, unavailable.pk, empty.pk)
    )

    updated, skipped = playlist_item_service.set_published(
        queryset,
        value=True,
        actor=actor,
    )

    ready.refresh_from_db()
    unavailable.refresh_from_db()
    empty.refresh_from_db()
    assert (updated, skipped) == (1, 2)
    assert ready.is_published is True
    assert unavailable.is_published is False
    assert empty.is_published is False


def test_recalculate_positions_uses_stable_service_order():
    playlist = PlaylistFactory()
    first = PlaylistItemFactory(playlist=playlist, position=2)
    second = PlaylistItemFactory(playlist=playlist, position=5)

    changed = playlist_item_service.recalculate_positions(
        playlist=playlist,
        actor=playlist.owner,
    )

    first.refresh_from_db()
    second.refresh_from_db()
    assert changed == 2
    assert (first.position, second.position) == (1, 2)


def test_remove_unavailable_tracks_rewrites_positions():
    playlist = PlaylistFactory(is_published=False)
    unavailable = PlaylistItemFactory(
        playlist=playlist,
        position=1,
        track__is_published=False,
        track__published_at=None,
    )
    available = PlaylistItemFactory(playlist=playlist, position=2)

    removed = playlist_item_service.remove_unavailable(
        playlist=playlist,
        actor=playlist.owner,
    )

    available.refresh_from_db()
    assert removed == 1
    assert not playlist.items.filter(pk=unavailable.pk).exists()
    assert available.position == 1


def test_duplicate_playlist_preserves_order_but_is_private_draft():
    source = PlaylistFactory(is_published=True)
    first = PlaylistItemFactory(playlist=source, position=1)
    second = PlaylistItemFactory(playlist=source, position=2)

    duplicate = playlist_item_service.duplicate(
        playlist=source,
        user=source.owner,
    )

    assert duplicate.is_published is False
    assert duplicate.is_featured is False
    assert duplicate.visibility == "private"
    assert list(duplicate.items.values_list("track_id", flat=True)) == [
        first.track_id,
        second.track_id,
    ]


def test_reorder_rejects_stale_track_set_after_another_editor_removes_track():
    playlist = PlaylistFactory()
    first = PlaylistItemFactory(playlist=playlist, position=1)
    removed = PlaylistItemFactory(playlist=playlist, position=2)
    stale_order = [removed.track_id, first.track_id]

    playlist_item_service.remove(
        playlist=playlist,
        track=removed.track,
        actor=playlist.owner,
    )

    with pytest.raises(ValidationError, match="every current track"):
        playlist_item_service.reorder(
            playlist=playlist,
            track_ids=stale_order,
            actor=playlist.owner,
        )

    assert list(playlist.items.values_list("track_id", "position")) == [
        (first.track_id, 1)
    ]
