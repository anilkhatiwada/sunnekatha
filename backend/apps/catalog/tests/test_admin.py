from datetime import timedelta
from unittest.mock import Mock

import pytest
from django.contrib import admin
from django.urls import reverse
from django.utils import timezone
from unfold.contrib.filters.admin import (
    AutocompleteSelectFilter,
    BooleanRadioFilter,
    MultipleChoicesDropdownFilter,
    RangeDateTimeFilter,
    RangeNumericFilter,
)

from apps.accounts.models import User
from apps.accounts.tests.factories import UserFactory
from apps.catalog.admin import (
    AlbumAdmin,
    LiteraryWorkAdmin,
    LiteraryWorkTrackInline,
    PublicationStatusFilter,
)
from apps.catalog.models import Album, LiteraryWork
from apps.catalog.services import EditorialResult, EditorialService
from apps.catalog.tests.factories import AudioTrackFactory, LiteraryWorkFactory


def test_catalog_models_are_registered_in_admin():
    assert isinstance(admin.site._registry[LiteraryWork], LiteraryWorkAdmin)
    assert isinstance(admin.site._registry[Album], AlbumAdmin)


def test_literary_work_admin_has_requested_columns_filters_search_and_fieldsets():
    model_admin = admin.site._registry[LiteraryWork]

    assert model_admin.list_display == (
        "cover_thumbnail",
        "title_ne",
        "title_en",
        "category",
        "author",
        "language",
        "copyright_status",
        "track_count",
        "publication_badge",
        "featured_badge",
        "published_at",
    )
    assert model_admin.list_filter == (
        ("category", AutocompleteSelectFilter),
        PublicationStatusFilter,
        ("is_featured", BooleanRadioFilter),
        ("copyright_status", MultipleChoicesDropdownFilter),
        ("language", AutocompleteSelectFilter),
        ("author", AutocompleteSelectFilter),
        ("publication_year", RangeNumericFilter),
        ("published_at", RangeDateTimeFilter),
    )
    assert model_admin.search_fields == (
        "=id",
        "slug",
        "title_ne",
        "title_en",
        "author__name_ne",
        "author__name_en",
        "copyright_owner",
    )
    assert [fieldset[0] for fieldset in model_admin.fieldsets] == [
        "Basic Information",
        "Author and Classification",
        "Description",
        "Copyright and Rights",
        "Artwork",
        "Publication",
        "System Information",
    ]
    assert model_admin.inlines == (LiteraryWorkTrackInline,)
    assert {"slug", "created_at", "updated_at", "cover_preview"} <= set(
        model_admin.readonly_fields
    )


@pytest.mark.django_db
def test_literary_work_admin_queryset_annotates_track_count(rf):
    work = LiteraryWorkFactory()
    AudioTrackFactory.create_batch(2, work=work)
    model_admin = admin.site._registry[LiteraryWork]
    request = rf.get("/admin/catalog/literarywork/")
    request.user = User.objects.create_superuser(
        email="work-admin@example.com",
        username="work-admin",
        display_name="Work Admin",
        password="test-password",
    )

    annotated = model_admin.get_queryset(request).get(pk=work.pk)

    assert model_admin.track_count(annotated) == 2


@pytest.mark.django_db
def test_literary_work_admin_badges_and_public_preview():
    model_admin = admin.site._registry[LiteraryWork]
    draft = LiteraryWorkFactory(is_published=False, published_at=None)
    scheduled = LiteraryWorkFactory(published_at=timezone.now() + timedelta(days=1))
    published = LiteraryWorkFactory()

    assert model_admin.publication_badge(draft) == ("draft", "Draft")
    assert model_admin.publication_badge(scheduled) == ("scheduled", "Scheduled")
    assert model_admin.publication_badge(published) == ("published", "Published")
    assert model_admin.featured_badge(draft) == ("standard", "Standard")
    assert "publicly published" in model_admin.preview_public_page(draft)
    assert reverse("catalog:work-detail", kwargs={"slug": published.slug}) in str(
        model_admin.preview_public_page(published)
    )


@pytest.mark.django_db
def test_literary_work_publish_actions_delegate_to_editorial_service(rf, monkeypatch):
    model_admin = admin.site._registry[LiteraryWork]
    model_admin.message_user = Mock()
    request = rf.post(
        "/admin/catalog/literarywork/",
        {"confirm_bulk_action": "1"},
    )
    request.user = UserFactory(is_staff=True, is_superuser=True)
    work = LiteraryWorkFactory(is_published=False, published_at=None)
    queryset = LiteraryWork.objects.filter(pk=work.pk)
    publish = Mock(return_value=EditorialResult(updated=1))
    unpublish = Mock(return_value=EditorialResult(updated=1))
    monkeypatch.setattr(EditorialService, "publish_works", publish)
    monkeypatch.setattr(EditorialService, "unpublish_works", unpublish)

    model_admin.publish_selected(request, queryset)
    model_admin.unpublish_selected(request, queryset)

    publish.assert_called_once_with(queryset, actor=request.user)
    unpublish.assert_called_once_with(queryset, actor=request.user)
