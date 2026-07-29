import pytest

from apps.accounts.tests.factories import UserFactory
from apps.narrators.services import (
    NarratorEditorialResult,
    narrator_editorial_service,
)
from apps.narrators.tests.factories import NarratorFactory

pytestmark = pytest.mark.django_db


def test_narrator_editorial_transitions_are_idempotent():
    actor = UserFactory(is_staff=True, is_superuser=True)
    narrator = NarratorFactory(is_featured=False, is_verified=False)
    queryset = narrator.__class__.objects.filter(pk=narrator.pk)

    featured = narrator_editorial_service.set_featured(
        queryset,
        value=True,
        actor=actor,
    )
    repeated = narrator_editorial_service.set_featured(
        queryset,
        value=True,
        actor=actor,
    )
    verified = narrator_editorial_service.set_verified(queryset, actor=actor)

    narrator.refresh_from_db()
    assert featured == NarratorEditorialResult(updated=1, skipped=0)
    assert repeated == NarratorEditorialResult(updated=0, skipped=1)
    assert verified == NarratorEditorialResult(updated=1, skipped=0)
    assert narrator.is_featured is True
    assert narrator.is_verified is True
