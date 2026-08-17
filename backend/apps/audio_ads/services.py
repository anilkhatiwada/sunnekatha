from dataclasses import dataclass
from uuid import UUID

from django.db import IntegrityError, transaction
from django.db.models import Max, Q

from apps.audio_ads.models import AudioAdvertisement, AudioAdvertisementPlayback
from apps.catalog.models import AudioTrack


@dataclass(frozen=True)
class AdSelection:
    advertisement: AudioAdvertisement | None
    reason: str


class AudioAdvertisementService:
    minimum_global_gap = 2

    def select_for_playback(
        self,
        *,
        session_id: UUID,
        playback_sequence: int,
    ) -> AdSelection:
        enabled = list(
            AudioAdvertisement.objects.filter(is_enabled=True)
            .exclude(audio_file="")
            .annotate(
                session_last_sequence=Max(
                    "playbacks__playback_sequence",
                    filter=Q(playbacks__session_id=session_id),
                ),
            )
        )
        if not enabled:
            return AdSelection(None, "no_enabled_ads")

        latest_any = (
            AudioAdvertisementPlayback.objects.filter(session_id=session_id)
            .order_by("-playback_sequence")
            .values_list("playback_sequence", flat=True)
            .first()
        )
        if (
            latest_any is not None
            and playback_sequence - latest_any < self.minimum_global_gap
        ):
            return AdSelection(None, "global_frequency_gap")

        eligible = []
        for advertisement in enabled:
            last_sequence = advertisement.session_last_sequence
            is_due = (
                playback_sequence >= advertisement.frequency
                if last_sequence is None
                else playback_sequence - last_sequence >= advertisement.frequency
            )
            if is_due:
                eligible.append(advertisement)
        if not eligible:
            return AdSelection(None, "frequency_not_reached")

        eligible.sort(
            key=lambda advertisement: (
                advertisement.session_last_sequence is not None,
                advertisement.session_last_sequence or 0,
                str(advertisement.pk),
            )
        )
        return AdSelection(eligible[0], "eligible")

    @transaction.atomic
    def record_started(
        self,
        *,
        advertisement: AudioAdvertisement,
        session_id: UUID,
        playback_sequence: int,
        source: str,
        track: AudioTrack | None,
        user,
    ) -> tuple[AudioAdvertisementPlayback, bool]:
        try:
            return AudioAdvertisementPlayback.objects.get_or_create(
                advertisement=advertisement,
                session_id=session_id,
                playback_sequence=playback_sequence,
                defaults={
                    "source": source,
                    "track": track,
                    "user": user if getattr(user, "is_authenticated", False) else None,
                },
            )
        except IntegrityError:
            return (
                AudioAdvertisementPlayback.objects.get(
                    advertisement=advertisement,
                    session_id=session_id,
                    playback_sequence=playback_sequence,
                ),
                False,
            )


audio_advertisement_service = AudioAdvertisementService()
