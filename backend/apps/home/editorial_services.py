from dataclasses import dataclass
from uuid import UUID

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import F, Max
from django.utils import timezone

from apps.common.audit import administrative_audit_service
from apps.common.cache import public_cache_invalidation
from apps.common.models import AdministrativeAuditAction
from apps.home.models import (
    HomeSection,
    HomeSectionItem,
    HomeSectionLayout,
    HomeSectionSource,
    HomeSectionType,
)
from apps.playlists.models import PlaylistType, PlaylistVisibility


@dataclass(frozen=True)
class HomeSectionItemInput:
    """Validated editorial intent for one ordered homepage item."""

    item_id: UUID | None
    target_field: str
    target_id: UUID


class HomeEditorialService:
    """Transactional mutations used by editorial interfaces."""

    @staticmethod
    def _authorize(actor):
        if not (
            actor
            and actor.is_authenticated
            and actor.is_active
            and actor.is_staff
            and actor.has_perm("home.change_homesection")
        ):
            raise PermissionDenied("Homepage editorial permission is required.")

    @transaction.atomic
    def replace_items(
        self,
        *,
        section: HomeSection,
        items: list[HomeSectionItemInput],
        actor=None,
    ) -> list[HomeSectionItem]:
        self._authorize(actor)
        locked_section = HomeSection.objects.select_for_update().get(pk=section.pk)
        allowed_targets = HomeSectionItem.SECTION_TARGETS[locked_section.section_type]
        supplied_ids = [item.item_id for item in items if item.item_id is not None]
        if len(supplied_ids) != len(set(supplied_ids)):
            raise ValidationError("A homepage item may only appear once.")
        invalid_targets = {
            item.target_field
            for item in items
            if item.target_field not in allowed_targets
        }
        if invalid_targets:
            raise ValidationError(
                "Selected content is incompatible with this homepage section type."
            )

        existing = {
            item.pk: item
            for item in HomeSectionItem.objects.select_for_update().filter(
                section=locked_section
            )
        }
        unknown_ids = set(supplied_ids) - set(existing)
        if unknown_ids:
            raise ValidationError(
                "Homepage items changed while you were editing. Reload and try again."
            )

        HomeSectionItem.objects.filter(section=locked_section).exclude(
            pk__in=supplied_ids
        ).delete()
        maximum = (
            HomeSectionItem.objects.filter(section=locked_section).aggregate(
                value=Max("position")
            )["value"]
            or 0
        )
        HomeSectionItem.objects.filter(section=locked_section).update(
            position=F("position") + maximum + len(items) + 1
        )

        target_fields = HomeSectionItem.TARGET_FIELDS
        for position, item_input in enumerate(items, start=1):
            values = {f"{field}_id": None for field in target_fields}
            values[f"{item_input.target_field}_id"] = item_input.target_id
            if item_input.item_id is None:
                HomeSectionItem.objects.create(
                    section=locked_section,
                    position=position,
                    **values,
                )
                continue
            item = existing[item_input.item_id]
            item.position = position
            for field, value in values.items():
                setattr(item, field, value)
            item.save(update_fields=("position", *values.keys(), "updated_at"))

        result = list(
            HomeSectionItem.objects.filter(section=locked_section)
            .select_related(*HomeSectionItem.TARGET_FIELDS)
            .order_by("position", "id")
        )
        administrative_audit_service.record(
            actor=actor,
            action=AdministrativeAuditAction.HOMEPAGE_CHANGED,
            obj=locked_section,
            reason="Homepage section items updated.",
            before={"position": [str(item_id) for item_id in existing]},
            after={"position": [str(item.pk) for item in result]},
        )
        return result

    @transaction.atomic
    def set_active(self, *, sections, value: bool, actor=None) -> int:
        self._authorize(actor)
        targets = list(sections.exclude(is_active=value))
        updated = sections.exclude(is_active=value).update(
            is_active=value,
            updated_at=timezone.now(),
        )
        if updated:
            public_cache_invalidation.for_model(HomeSection)
            for section in targets:
                administrative_audit_service.record(
                    actor=actor,
                    action=AdministrativeAuditAction.HOMEPAGE_CHANGED,
                    obj=section,
                    reason=(
                        "Homepage section activated."
                        if value
                        else "Homepage section deactivated."
                    ),
                    before={"is_active": not value},
                    after={"is_active": value},
                )
        return updated

    @transaction.atomic
    def add_new_playlists(self, *, playlists, actor=None):
        """Add valid editorial playlists to the managed homepage rail."""
        self._authorize(actor)
        selected = list(playlists.select_for_update().order_by("created_at", "id"))
        if not selected:
            raise ValidationError("Select at least one playlist.")
        invalid = [
            playlist
            for playlist in selected
            if playlist.playlist_type != PlaylistType.EDITORIAL
            or playlist.visibility != PlaylistVisibility.PUBLIC
            or not playlist.is_published
        ]
        if invalid:
            raise ValidationError(
                "Only published, public editorial playlists can appear on the homepage."
            )

        section, _ = HomeSection.objects.select_for_update().get_or_create(
            identifier="new-playlists",
            defaults={
                "title_ne": "नयाँ प्लेलिस्टहरू",
                "title_en": "New Playlists",
                "subtitle_en": "Fresh editorial collections from SunneKatha",
                "section_type": HomeSectionType.PLAYLISTS,
                "content_source": HomeSectionSource.EDITORIAL,
                "layout": HomeSectionLayout.RAIL,
                "max_items": 12,
                "sort_order": 50,
                "is_active": True,
            },
        )
        if (
            section.section_type != HomeSectionType.PLAYLISTS
            or section.content_source != HomeSectionSource.EDITORIAL
        ):
            raise ValidationError(
                "The new-playlists homepage identifier is used by an "
                "incompatible section."
            )

        existing = list(section.items.order_by("position", "id"))
        existing_playlist_ids = {
            item.playlist_id for item in existing if item.playlist_id is not None
        }
        additions = [
            playlist
            for playlist in selected
            if playlist.pk not in existing_playlist_ids
        ]
        if len(existing) + len(additions) > section.max_items:
            raise ValidationError(
                f"The homepage section supports at most {section.max_items} playlists."
            )
        inputs = [
            HomeSectionItemInput(item.pk, "playlist", item.playlist_id)
            for item in existing
        ] + [
            HomeSectionItemInput(None, "playlist", playlist.pk)
            for playlist in additions
        ]
        self.replace_items(section=section, items=inputs, actor=actor)
        return section, len(additions)


home_editorial_service = HomeEditorialService()
