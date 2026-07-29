from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import F
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.catalog.models import AudioTrack
from apps.library.models import (
    ListeningHistory,
    PlaybackEvent,
    PlaybackEventType,
    PlaybackSession,
)

EVENT_DUPLICATE_WINDOW = timedelta(seconds=2)


class PlaybackSessionService:
    @transaction.atomic
    def start(self, *, user, track, device_id, position_seconds=0, client_event_id=""):
        now = timezone.now()
        session, created = PlaybackSession.objects.get_or_create(
            user=user,
            track=track,
            device_id=device_id,
            ended_at__isnull=True,
            defaults={
                "started_at": now,
                "last_activity_at": now,
            },
        )
        if created:
            AudioTrack.objects.filter(pk=track.pk).update(
                play_count_cache=F("play_count_cache") + 1
            )
            self._record_event(
                session=session,
                event_type=PlaybackEventType.STARTED,
                position_seconds=position_seconds,
                client_event_id=client_event_id,
            )
            self._record_history_start(session=session, now=now)
        return session, created

    @transaction.atomic
    def update(
        self,
        *,
        session,
        listened_seconds,
        event_type=None,
        position_seconds=None,
        client_event_id="",
        metadata=None,
    ):
        locked = PlaybackSession.objects.select_for_update().get(pk=session.pk)
        if locked.ended_at is not None:
            raise ValidationError({"session": "Playback session has already ended."})
        listened = Decimal(str(listened_seconds))
        if listened < 0:
            raise ValidationError(
                {"listenedSeconds": "Listened seconds cannot be negative."}
            )
        locked.listened_seconds = max(locked.listened_seconds, listened)
        locked.last_activity_at = timezone.now()
        locked.save(
            update_fields=("listened_seconds", "last_activity_at", "updated_at")
        )
        if event_type:
            self._record_event(
                session=locked,
                event_type=event_type,
                position_seconds=position_seconds,
                client_event_id=client_event_id,
                metadata=metadata,
            )
        return locked

    @transaction.atomic
    def end(
        self,
        *,
        session,
        listened_seconds=None,
        completed=False,
        position_seconds=None,
        client_event_id="",
    ):
        locked = PlaybackSession.objects.select_for_update().get(pk=session.pk)
        if locked.ended_at is not None:
            return locked, False
        if listened_seconds is not None:
            listened = Decimal(str(listened_seconds))
            if listened < 0:
                raise ValidationError(
                    {"listenedSeconds": "Listened seconds cannot be negative."}
                )
            locked.listened_seconds = max(locked.listened_seconds, listened)
        now = timezone.now()
        locked.last_activity_at = now
        locked.ended_at = now
        locked.completed = completed
        locked.save(
            update_fields=(
                "listened_seconds",
                "last_activity_at",
                "ended_at",
                "completed",
                "updated_at",
            )
        )
        self._record_event(
            session=locked,
            event_type=(
                PlaybackEventType.COMPLETED if completed else PlaybackEventType.STOPPED
            ),
            position_seconds=position_seconds,
            client_event_id=client_event_id,
        )
        history, created = ListeningHistory.objects.get_or_create(
            user=locked.user,
            track=locked.track,
            defaults={
                "first_listened_at": locked.started_at,
                "last_listened_at": now,
                "total_listened_seconds": locked.listened_seconds,
                "play_count": 1,
                "completion_count": int(completed),
            },
        )
        if not created:
            ListeningHistory.objects.filter(pk=history.pk).update(
                last_listened_at=now,
                total_listened_seconds=(
                    F("total_listened_seconds") + locked.listened_seconds
                ),
                completion_count=F("completion_count") + int(completed),
                updated_at=now,
            )
        return locked, True

    @staticmethod
    def _record_history_start(*, session, now):
        history, created = ListeningHistory.objects.get_or_create(
            user=session.user,
            track=session.track,
            defaults={
                "first_listened_at": now,
                "last_listened_at": now,
                "total_listened_seconds": 0,
                "play_count": 1,
                "completion_count": 0,
            },
        )
        if not created:
            ListeningHistory.objects.filter(pk=history.pk).update(
                last_listened_at=now,
                play_count=F("play_count") + 1,
                updated_at=now,
            )

    def _record_event(
        self,
        *,
        session,
        event_type,
        position_seconds=None,
        client_event_id="",
        metadata=None,
    ):
        position = (
            Decimal(str(position_seconds)) if position_seconds is not None else None
        )
        if position is not None and position < 0:
            raise ValidationError(
                {"positionSeconds": "Event position cannot be negative."}
            )
        if client_event_id:
            event, _ = PlaybackEvent.objects.get_or_create(
                session=session,
                deduplication_key=client_event_id,
                defaults={
                    "event_type": event_type,
                    "position_seconds": position,
                    "metadata": metadata or {},
                },
            )
            return event
        cutoff = timezone.now() - EVENT_DUPLICATE_WINDOW
        duplicate = PlaybackEvent.objects.filter(
            session=session,
            event_type=event_type,
            position_seconds=position,
            occurred_at__gte=cutoff,
        ).first()
        if duplicate:
            return duplicate
        return PlaybackEvent.objects.create(
            session=session,
            event_type=event_type,
            position_seconds=position,
            metadata=metadata or {},
        )


playback_session_service = PlaybackSessionService()
