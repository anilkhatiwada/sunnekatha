from dataclasses import dataclass

from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone

from apps.common.cache import public_cache_invalidation


@dataclass(frozen=True)
class NarratorEditorialResult:
    updated: int
    skipped: int = 0


class NarratorEditorialService:
    """Transactional editorial transitions for narrator profiles."""

    @staticmethod
    def _authorize(actor):
        if not (
            actor
            and actor.is_authenticated
            and actor.is_active
            and actor.is_staff
            and actor.has_perm("narrators.change_narrator")
        ):
            raise PermissionDenied("Narrator editorial permission is required.")

    @staticmethod
    @transaction.atomic
    def set_featured(queryset, *, value, actor):
        NarratorEditorialService._authorize(actor)
        total = queryset.count()
        updated = queryset.exclude(is_featured=value).update(
            is_featured=value,
            updated_at=timezone.now(),
        )
        public_cache_invalidation.for_model(queryset.model)
        return NarratorEditorialResult(updated, total - updated)

    @staticmethod
    @transaction.atomic
    def set_verified(queryset, *, actor, value=True):
        NarratorEditorialService._authorize(actor)
        total = queryset.count()
        updated = queryset.exclude(is_verified=value).update(
            is_verified=value,
            updated_at=timezone.now(),
        )
        public_cache_invalidation.for_model(queryset.model)
        return NarratorEditorialResult(updated, total - updated)


narrator_editorial_service = NarratorEditorialService()
