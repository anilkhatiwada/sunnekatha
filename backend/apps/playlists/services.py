from django.db import transaction
from django.db.models import F, Max, Q
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.catalog.models import AudioTrack, LiteraryWork, TrackProcessingStatus
from apps.common.audit import administrative_audit_service
from apps.common.cache import public_cache_invalidation
from apps.common.models import AdministrativeAuditAction
from apps.notifications.services import notification_service
from apps.playlists.models import Playlist, PlaylistItem, PlaylistVisibility


class PlaylistItemService:
    @staticmethod
    def _authorize(*, playlist, actor):
        is_owner = bool(
            actor
            and actor.is_authenticated
            and actor.is_active
            and playlist.owner_id == actor.pk
        )
        is_authorized_staff = bool(
            actor
            and actor.is_authenticated
            and actor.is_active
            and actor.is_staff
            and actor.has_perm("playlists.change_playlist")
        )
        if not (is_owner or is_authorized_staff):
            raise PermissionDenied("You cannot manage this playlist.")

    @transaction.atomic
    def add(self, *, playlist: Playlist, track: AudioTrack, user) -> PlaylistItem:
        self._authorize(playlist=playlist, actor=user)
        locked = Playlist.objects.select_for_update().get(pk=playlist.pk)
        if PlaylistItem.objects.filter(playlist=locked, track=track).exists():
            raise ValidationError({"trackId": "Track is already in this playlist."})
        last = (
            PlaylistItem.objects.filter(playlist=locked).aggregate(Max("position"))[
                "position__max"
            ]
            or 0
        )
        item = PlaylistItem.objects.create(
            playlist=locked,
            track=track,
            position=last + 1,
            added_by=user,
        )
        notification_service.playlist_updated(locked)
        return item

    @transaction.atomic
    def add_work(self, *, playlist: Playlist, work: LiteraryWork, user) -> PlaylistItem:
        self._authorize(playlist=playlist, actor=user)
        locked = Playlist.objects.select_for_update().get(pk=playlist.pk)
        if PlaylistItem.objects.filter(playlist=locked, work=work).exists():
            raise ValidationError({"workId": "Work is already in this playlist."})
        last = (
            PlaylistItem.objects.filter(playlist=locked).aggregate(Max("position"))[
                "position__max"
            ]
            or 0
        )
        item = PlaylistItem.objects.create(
            playlist=locked, work=work, position=last + 1, added_by=user
        )
        notification_service.playlist_updated(locked)
        return item

    @transaction.atomic
    def remove(self, *, playlist: Playlist, track: AudioTrack, actor) -> None:
        self._authorize(playlist=playlist, actor=actor)
        Playlist.objects.select_for_update().get(pk=playlist.pk)
        deleted, _ = PlaylistItem.objects.filter(
            playlist=playlist,
            track=track,
        ).delete()
        if not deleted:
            raise ValidationError({"trackId": "Track is not in this playlist."})
        self._rewrite_positions(playlist)
        notification_service.playlist_updated(playlist)

    @transaction.atomic
    def remove_work(self, *, playlist: Playlist, work: LiteraryWork, actor) -> None:
        self._authorize(playlist=playlist, actor=actor)
        Playlist.objects.select_for_update().get(pk=playlist.pk)
        deleted, _ = PlaylistItem.objects.filter(playlist=playlist, work=work).delete()
        if not deleted:
            raise ValidationError({"workId": "Work is not in this playlist."})
        self._rewrite_positions(playlist)
        notification_service.playlist_updated(playlist)

    @transaction.atomic
    def reorder(self, *, playlist: Playlist, track_ids: list, actor=None) -> None:
        self._authorize(playlist=playlist, actor=actor)
        Playlist.objects.select_for_update().get(pk=playlist.pk)
        items = list(
            PlaylistItem.objects.select_for_update()
            .filter(playlist=playlist)
            .order_by("position")
        )
        existing = [item.track_id for item in items]
        if len(track_ids) != len(set(track_ids)):
            raise ValidationError({"trackIds": "Track IDs must be unique."})
        if set(track_ids) != set(existing) or len(track_ids) != len(existing):
            raise ValidationError(
                {"trackIds": "Provide every current track exactly once."}
            )
        by_track = {item.track_id: item for item in items}
        # Offset first so the per-playlist unique position constraint remains valid.
        PlaylistItem.objects.filter(playlist=playlist).update(
            position=F("position") + len(items) + 1
        )
        for position, track_id in enumerate(track_ids, start=1):
            item = by_track[track_id]
            item.position = position
            item.save(update_fields=["position"])
        notification_service.playlist_updated(playlist)
        administrative_audit_service.record(
            actor=actor,
            action=AdministrativeAuditAction.PLAYLIST_REORDERED,
            obj=playlist,
            reason="Playlist tracks reordered.",
            before={"position": [str(track_id) for track_id in existing]},
            after={"position": [str(track_id) for track_id in track_ids]},
        )

    @transaction.atomic
    def reorder_items(self, *, playlist: Playlist, item_ids: list, actor=None) -> None:
        self._authorize(playlist=playlist, actor=actor)
        Playlist.objects.select_for_update().get(pk=playlist.pk)
        items = list(PlaylistItem.objects.select_for_update().filter(playlist=playlist))
        existing = [item.pk for item in items]
        if len(item_ids) != len(set(item_ids)) or set(item_ids) != set(existing):
            raise ValidationError(
                {"itemIds": "Provide every current playlist item exactly once."}
            )
        by_id = {item.pk: item for item in items}
        PlaylistItem.objects.filter(playlist=playlist).update(
            position=F("position") + len(items) + 1
        )
        for position, item_id in enumerate(item_ids, start=1):
            item = by_id[item_id]
            item.position = position
            item.save(update_fields=("position",))
        notification_service.playlist_updated(playlist)
        administrative_audit_service.record(
            actor=actor,
            action=AdministrativeAuditAction.PLAYLIST_REORDERED,
            obj=playlist,
            reason="Playlist items reordered.",
            before={"position": [str(item_id) for item_id in existing]},
            after={"position": [str(item_id) for item_id in item_ids]},
        )

    @transaction.atomic
    def recalculate_positions(self, *, playlist: Playlist, actor) -> int:
        self._authorize(playlist=playlist, actor=actor)
        locked = Playlist.objects.select_for_update().get(pk=playlist.pk)
        items = list(
            PlaylistItem.objects.select_for_update()
            .filter(playlist=locked)
            .order_by("position", "created_at", "id")
        )
        changed = sum(item.position != index for index, item in enumerate(items, 1))
        if changed:
            maximum = max((item.position for item in items), default=0)
            PlaylistItem.objects.filter(playlist=locked).update(
                position=F("position") + maximum + len(items) + 1
            )
            for position, item in enumerate(items, 1):
                item.position = position
                item.save(update_fields=("position",))
            notification_service.playlist_updated(locked)
        return changed

    @transaction.atomic
    def remove_unavailable(self, *, playlist: Playlist, actor) -> int:
        self._authorize(playlist=playlist, actor=actor)
        locked = Playlist.objects.select_for_update().get(pk=playlist.pk)
        now = timezone.now()
        valid_tracks = Q(
            track__is_published=True,
            track__processing_status=TrackProcessingStatus.READY,
            track__published_at__lte=now,
        ) & (Q(track__stream_file_low__gt="") | Q(track__stream_file_high__gt=""))
        valid_works = Q(work__in=LiteraryWork.objects.discoverable())
        unavailable = PlaylistItem.objects.filter(playlist=locked).exclude(
            valid_tracks | valid_works
        )
        removed, _ = unavailable.delete()
        if removed:
            self.recalculate_positions(playlist=locked, actor=actor)
            if (
                locked.is_published
                and not PlaylistItem.objects.filter(playlist=locked).exists()
            ):
                locked.is_published = False
                locked.save(update_fields=("is_published", "updated_at"))
            notification_service.playlist_updated(locked)
        return removed

    @transaction.atomic
    def duplicate(self, *, playlist: Playlist, user) -> Playlist:
        self._authorize(playlist=playlist, actor=user)
        source = Playlist.objects.select_for_update().get(pk=playlist.pk)
        duplicate = Playlist.objects.create(
            owner=source.owner,
            title_ne=f"{source.title_ne} (प्रतिलिपि)",
            title_en=source.title_en,
            description_ne=source.description_ne,
            description_en=source.description_en,
            cover_image=source.cover_image,
            playlist_type=source.playlist_type,
            visibility=PlaylistVisibility.PRIVATE,
            is_featured=False,
            is_published=False,
        )
        PlaylistItem.objects.bulk_create(
            [
                PlaylistItem(
                    playlist=duplicate,
                    track_id=item.track_id,
                    work_id=item.work_id,
                    position=item.position,
                    added_by=user,
                )
                for item in source.items.all()
            ]
        )
        public_cache_invalidation.for_model(Playlist)
        return duplicate

    @transaction.atomic
    def set_published(self, queryset, *, value: bool, actor=None):
        if not (
            actor
            and actor.is_authenticated
            and actor.is_active
            and actor.is_staff
            and actor.has_perm("playlists.change_playlist")
        ):
            raise PermissionDenied("Playlist publication permission is required.")
        # Admin changelists add annotations, select_related(), and deferred fields.
        # Materialize only the selected identities, then perform publication work on
        # a clean queryset so row locking cannot inherit incompatible query options.
        selected_ids = list(dict.fromkeys(queryset.values_list("pk", flat=True)))
        total = len(selected_ids)
        locked_queryset = Playlist.objects.select_for_update().filter(
            pk__in=selected_ids
        )
        if not value:
            targets = list(locked_queryset.filter(is_published=True))
            updated = locked_queryset.filter(is_published=True).update(
                is_published=False,
                updated_at=timezone.now(),
            )
            for playlist in targets:
                administrative_audit_service.record(
                    actor=actor,
                    action=AdministrativeAuditAction.UNPUBLISHED,
                    obj=playlist,
                    reason="Playlist unpublished.",
                    before={"is_published": True},
                    after={"is_published": False},
                )
            public_cache_invalidation.for_model(Playlist)
            return updated, total - updated

        now = timezone.now()
        eligible_ids = []
        for playlist in locked_queryset.only("pk"):
            items = PlaylistItem.objects.filter(playlist=playlist)
            has_items = items.exists()
            unavailable_tracks = (
                items.filter(track__isnull=False)
                .filter(
                    Q(track__is_published=False)
                    | ~Q(track__processing_status=TrackProcessingStatus.READY)
                    | Q(track__published_at__isnull=True)
                    | Q(track__published_at__gt=now)
                    | (Q(track__stream_file_low="") & Q(track__stream_file_high=""))
                )
                .exists()
            )
            unavailable_works = (
                items.filter(work__isnull=False)
                .exclude(work__in=LiteraryWork.objects.discoverable())
                .exists()
            )
            has_unavailable = unavailable_tracks or unavailable_works
            if has_items and not has_unavailable:
                eligible_ids.append(playlist.pk)
        targets = list(locked_queryset.filter(pk__in=eligible_ids, is_published=False))
        updated = locked_queryset.filter(
            pk__in=eligible_ids, is_published=False
        ).update(
            is_published=True,
            updated_at=now,
        )
        for playlist in targets:
            administrative_audit_service.record(
                actor=actor,
                action=AdministrativeAuditAction.PUBLISHED,
                obj=playlist,
                reason="Playlist published.",
                before={"is_published": False},
                after={"is_published": True},
            )
        public_cache_invalidation.for_model(Playlist)
        return updated, total - updated

    @staticmethod
    def _rewrite_positions(playlist: Playlist) -> None:
        items = list(PlaylistItem.objects.filter(playlist=playlist))
        for position, item in enumerate(items, start=1):
            if item.position != position:
                item.position = position
                item.save(update_fields=["position"])


playlist_item_service = PlaylistItemService()
