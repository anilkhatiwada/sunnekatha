from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.library.models import ListeningProgress

COMPLETION_THRESHOLD = Decimal("90")
POSITION_OVERSHOOT_TOLERANCE_SECONDS = Decimal("5")


class ListeningProgressService:
    @transaction.atomic
    def update(self, *, user, track, position_seconds, duration_seconds):
        position = Decimal(str(position_seconds))
        client_duration = Decimal(str(duration_seconds))
        if position < 0:
            raise ValidationError({"positionSeconds": "Position cannot be negative."})
        if client_duration <= 0:
            raise ValidationError(
                {"durationSeconds": "Duration must be greater than zero."}
            )

        duration = (
            Decimal(track.duration_seconds)
            if track.duration_seconds > 0
            else client_duration
        )
        if position > duration + POSITION_OVERSHOOT_TOLERANCE_SECONDS:
            raise ValidationError(
                {
                    "positionSeconds": (
                        "Position cannot be significantly greater than track duration."
                    )
                }
            )

        normalized_position = min(position, duration)
        percentage = ((normalized_position / duration) * Decimal("100")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        is_completed = percentage >= COMPLETION_THRESHOLD
        now = timezone.now()
        progress, _ = ListeningProgress.objects.update_or_create(
            user=user,
            track=track,
            defaults={
                "position_seconds": normalized_position,
                "duration_seconds": duration,
                "progress_percentage": percentage,
                "is_completed": is_completed,
                "last_listened_at": now,
            },
        )
        return progress

    def mark_completed(self, *, user, track):
        duration = Decimal(track.duration_seconds)
        if duration <= 0:
            existing = ListeningProgress.objects.filter(
                user=user,
                track=track,
            ).first()
            if not existing or existing.duration_seconds <= 0:
                raise ValidationError(
                    {"durationSeconds": "A positive track duration is required."}
                )
            duration = existing.duration_seconds
        return self.update(
            user=user,
            track=track,
            position_seconds=duration,
            duration_seconds=duration,
        )


listening_progress_service = ListeningProgressService()
