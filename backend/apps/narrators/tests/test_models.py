import pytest

from apps.accounts.tests.factories import UserFactory
from apps.narrators.tests.factories import NarratorFactory

pytestmark = pytest.mark.django_db


def test_narrator_generates_unique_unicode_slug():
    first = NarratorFactory(name_ne="आशा")
    second = NarratorFactory(name_ne="आशा")

    assert first.slug == "आशा"
    assert second.slug == "आशा-2"


def test_narrator_can_link_one_user():
    user = UserFactory()
    narrator = NarratorFactory(user=user)

    assert narrator.user == user
    assert user.narrator_profile == narrator
