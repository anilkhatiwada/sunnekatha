import pytest

from apps.accounts.tests.factories import UserFactory
from apps.authors.services import (
    AuthorEditorialResult,
    author_editorial_service,
)
from apps.authors.tests.factories import AuthorFactory

pytestmark = pytest.mark.django_db


def test_author_editorial_transitions_are_idempotent():
    actor = UserFactory(is_staff=True, is_superuser=True)
    author = AuthorFactory(is_featured=False, is_verified=False)
    queryset = author.__class__.objects.filter(pk=author.pk)

    featured = author_editorial_service.set_featured(
        queryset,
        value=True,
        actor=actor,
    )
    repeated = author_editorial_service.set_featured(
        queryset,
        value=True,
        actor=actor,
    )
    verified = author_editorial_service.set_verified(queryset, actor=actor)

    author.refresh_from_db()
    assert featured == AuthorEditorialResult(updated=1, skipped=0)
    assert repeated == AuthorEditorialResult(updated=0, skipped=1)
    assert verified == AuthorEditorialResult(updated=1, skipped=0)
    assert author.is_featured is True
    assert author.is_verified is True
