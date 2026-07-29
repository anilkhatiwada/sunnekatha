import pytest
from django.contrib import admin
from django.urls import reverse

from apps.accounts.tests.factories import UserFactory
from apps.authors.admin import (
    AuthorAdmin,
    HasCopyrightIssuesFilter,
    HasPublishedContentFilter,
)
from apps.authors.models import Author
from apps.authors.tests.factories import AuthorFactory
from apps.catalog.models import CopyrightStatus
from apps.catalog.tests.factories import AudioTrackFactory, LiteraryWorkFactory

pytestmark = pytest.mark.django_db


def test_author_admin_configuration_matches_editorial_workflow():
    model_admin = admin.site._registry[Author]

    assert isinstance(model_admin, AuthorAdmin)
    assert model_admin.list_display == (
        "image_thumbnail",
        "name_ne",
        "name_en",
        "work_count",
        "track_count",
        "is_featured",
        "is_verified",
        "copyright_issue_count",
        "created_at",
    )
    assert HasPublishedContentFilter in model_admin.list_filter
    assert HasCopyrightIssuesFilter in model_admin.list_filter
    assert "verify_selected" in model_admin.actions
    assert tuple(name for name, _ in model_admin.fieldsets) == (
        "Identity",
        "Biography",
        "Image",
        "Life Information",
        "Editorial Status",
        "Related Content",
        "System Information",
    )


def test_author_admin_annotates_work_track_and_unresolved_copyright_counts(rf):
    author = AuthorFactory()
    unresolved = LiteraryWorkFactory(
        author=author,
        copyright_status=CopyrightStatus.UNKNOWN,
    )
    LiteraryWorkFactory(
        author=author,
        copyright_status=CopyrightStatus.PERMISSION_GRANTED,
    )
    AudioTrackFactory(work=unresolved)
    request = rf.get("/")
    request.user = UserFactory(is_staff=True, is_superuser=True)
    model_admin = admin.site._registry[Author]

    result = model_admin.get_queryset(request).get(pk=author.pk)

    assert model_admin.work_count(result) == 2
    assert model_admin.track_count(result) == 1
    assert model_admin.copyright_issue_count(result) == 1


def test_author_admin_filters_published_content_and_copyright_issues(client):
    user = UserFactory(is_staff=True, is_superuser=True)
    expected = AuthorFactory()
    LiteraryWorkFactory(
        author=expected,
        is_published=True,
        copyright_status=CopyrightStatus.UNKNOWN,
    )
    other = AuthorFactory()
    LiteraryWorkFactory(
        author=other,
        is_published=False,
        published_at=None,
        copyright_status=CopyrightStatus.PERMISSION_GRANTED,
    )
    client.force_login(user)

    response = client.get(
        reverse("admin:authors_author_changelist"),
        {"has_published_content": "yes", "has_copyright_issues": "yes"},
    )

    assert response.status_code == 200
    assert list(response.context["cl"].result_list) == [expected]


def test_author_admin_related_and_public_links_use_named_routes():
    author = AuthorFactory()
    work = LiteraryWorkFactory(author=author)
    AudioTrackFactory(work=work)
    model_admin = admin.site._registry[Author]

    work_link = str(model_admin.related_literary_works(author))
    track_link = str(model_admin.related_audio_tracks(author))
    preview = str(model_admin.public_profile_preview(author))

    assert reverse("admin:catalog_literarywork_changelist") in work_link
    assert reverse("admin:catalog_audiotrack_changelist") in track_link
    assert reverse("authors:detail", kwargs={"slug": author.slug}) in preview


def test_author_admin_warns_about_similar_names_with_safe_change_link():
    existing = AuthorFactory(name_ne="पारिजात", name_en="Parijat")
    author = AuthorFactory(name_ne="पारिजात", name_en="Different spelling")
    model_admin = admin.site._registry[Author]

    warning = str(model_admin.duplicate_name_warning(author))

    assert "Review possible duplicates" in warning
    assert reverse("admin:authors_author_change", args=(existing.pk,)) in warning


def test_verify_action_updates_selected_authors(client):
    user = UserFactory(is_staff=True, is_superuser=True)
    author = AuthorFactory(is_verified=False)
    client.force_login(user)

    response = client.post(
        reverse("admin:authors_author_changelist"),
        {
            "action": "verify_selected",
            "_selected_action": str(author.pk),
        },
    )

    assert response.status_code == 302
    author.refresh_from_db()
    assert author.is_verified is True
