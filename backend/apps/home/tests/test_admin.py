from datetime import timedelta

import pytest
from django.contrib import admin
from django.test import RequestFactory
from django.urls import reverse
from django.utils import timezone

from apps.accounts.tests.factories import UserFactory
from apps.home.admin import (
    HomeSectionAdmin,
    HomeSectionItemAdminFormSet,
    HomeSectionItemInline,
)
from apps.home.models import HomeSection
from apps.home.tests.factories import HomeSectionFactory

pytestmark = pytest.mark.django_db


def test_home_section_admin_supports_ordering_and_items():
    model_admin = admin.site._registry[HomeSection]
    assert isinstance(model_admin, HomeSectionAdmin)
    assert "sort_order" in model_admin.list_editable
    assert model_admin.ordering_field == "sort_order"
    assert model_admin.hide_ordering_field is False
    assert HomeSectionItemInline in model_admin.inlines
    assert HomeSectionItemInline.ordering_field == "position"
    assert HomeSectionItemInline.hide_ordering_field is False
    assert HomeSectionItemInline.formset is HomeSectionItemAdminFormSet


def test_section_type_is_readonly_after_creation():
    model_admin = admin.site._registry[HomeSection]
    section = HomeSectionFactory()
    request = RequestFactory().get("/admin/")
    assert "section_type" in model_admin.get_readonly_fields(request, section)
    assert "section_type" not in model_admin.get_readonly_fields(request)


def test_schedule_badges_cover_editorial_states():
    model_admin = admin.site._registry[HomeSection]
    now = timezone.now()

    active = HomeSectionFactory()
    upcoming = HomeSectionFactory(starts_at=now + timedelta(hours=1))
    expired = HomeSectionFactory(
        starts_at=now - timedelta(hours=2),
        ends_at=now - timedelta(hours=1),
    )
    inactive = HomeSectionFactory(is_active=False)

    assert model_admin.schedule_badge(active) == ("active", "Active")
    assert model_admin.schedule_badge(upcoming) == ("upcoming", "Upcoming")
    assert model_admin.schedule_badge(expired) == ("expired", "Expired")
    assert model_admin.schedule_badge(inactive) == ("inactive", "Inactive")


def test_homepage_preview_uses_named_home_endpoint():
    model_admin = admin.site._registry[HomeSection]
    assert 'href="/api/v1/home/"' in str(model_admin.homepage_preview())


def test_editorial_section_admin_pages_render(client):
    user = UserFactory(is_staff=True, is_superuser=True)
    section = HomeSectionFactory()
    client.force_login(user)

    listing = client.get(reverse("admin:home_homesection_changelist"))
    change = client.get(reverse("admin:home_homesection_change", args=(section.pk,)))

    assert listing.status_code == 200
    assert change.status_code == 200
    assert "Preview homepage" in change.content.decode()
