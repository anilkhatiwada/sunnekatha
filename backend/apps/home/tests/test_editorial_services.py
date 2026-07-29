import pytest
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied, ValidationError

from apps.accounts.tests.factories import UserFactory
from apps.catalog.tests.factories import AudioTrackFactory
from apps.common.models import AdministrativeAudit, AdministrativeAuditAction
from apps.home.editorial_services import (
    HomeSectionItemInput,
    home_editorial_service,
)
from apps.home.models import HomeSectionItem, HomeSectionType
from apps.home.tests.factories import HomeSectionFactory
from apps.playlists.tests.factories import PlaylistFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def homepage_editor():
    actor = UserFactory(is_staff=True)
    actor.user_permissions.add(
        Permission.objects.get(
            content_type__app_label="home",
            codename="change_homesection",
        )
    )
    return actor


def as_input(item):
    field = next(
        field
        for field in item.TARGET_FIELDS
        if getattr(item, f"{field}_id") is not None
    )
    return HomeSectionItemInput(
        item_id=item.pk,
        target_field=field,
        target_id=getattr(item, f"{field}_id"),
    )


def test_home_editorial_service_rejects_staff_without_permission():
    section = HomeSectionFactory()

    with pytest.raises(PermissionDenied):
        home_editorial_service.set_active(
            sections=section.__class__.objects.filter(pk=section.pk),
            value=False,
            actor=UserFactory(is_staff=True),
        )


def test_replace_items_reorders_atomically_without_duplicate_positions(
    homepage_editor,
):
    section = HomeSectionFactory(section_type=HomeSectionType.TRACKS)
    first = HomeSectionItem.objects.create(
        section=section,
        track=AudioTrackFactory(),
        position=1,
    )
    second = HomeSectionItem.objects.create(
        section=section,
        track=AudioTrackFactory(),
        position=2,
    )

    result = home_editorial_service.replace_items(
        section=section,
        items=[as_input(second), as_input(first)],
        actor=homepage_editor,
    )

    assert [item.pk for item in result] == [second.pk, first.pk]
    assert [item.position for item in result] == [1, 2]


def test_replace_items_can_add_and_remove_content(homepage_editor):
    section = HomeSectionFactory(section_type=HomeSectionType.TRACKS)
    removed = HomeSectionItem.objects.create(
        section=section,
        track=AudioTrackFactory(),
        position=1,
    )
    track = AudioTrackFactory()

    result = home_editorial_service.replace_items(
        section=section,
        items=[
            HomeSectionItemInput(
                item_id=None,
                target_field="track",
                target_id=track.pk,
            )
        ],
        actor=homepage_editor,
    )

    assert not HomeSectionItem.objects.filter(pk=removed.pk).exists()
    assert len(result) == 1
    assert result[0].track_id == track.pk
    assert result[0].position == 1


def test_replace_items_rejects_content_incompatible_with_section(homepage_editor):
    section = HomeSectionFactory(section_type=HomeSectionType.TRACKS)

    with pytest.raises(ValidationError, match="incompatible"):
        home_editorial_service.replace_items(
            section=section,
            items=[
                HomeSectionItemInput(
                    item_id=None,
                    target_field="playlist",
                    target_id=PlaylistFactory().pk,
                )
            ],
            actor=homepage_editor,
        )


def test_homepage_activation_records_administrative_audit():
    actor = UserFactory(is_staff=True)
    actor.user_permissions.add(
        Permission.objects.get(
            content_type__app_label="home",
            codename="change_homesection",
        )
    )
    section = HomeSectionFactory(is_active=False)

    updated = home_editorial_service.set_active(
        sections=section.__class__.objects.filter(pk=section.pk),
        value=True,
        actor=actor,
    )

    assert updated == 1
    audit = AdministrativeAudit.objects.get(
        action=AdministrativeAuditAction.HOMEPAGE_CHANGED,
        object_id=str(section.pk),
    )
    assert audit.staff_user == actor
    assert audit.before_summary == {"is_active": False}
    assert audit.after_summary == {"is_active": True}
