import csv
from io import StringIO

import pytest
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.accounts.tests.factories import UserFactory
from apps.authors.models import Author
from apps.authors.tests.factories import AuthorFactory
from apps.common.metadata_transfer import preview_import
from apps.common.models import AdministrativeAudit, AdministrativeAuditAction

pytestmark = pytest.mark.django_db


AUTHOR_HEADER = (
    "slug,name_ne,name_en,biography_ne,biography_en,birth_date,death_date,country\n"
)


def transfer_staff(*, can_import=False, can_export=False):
    user = UserFactory(is_staff=True)
    codenames = ["view_author", "add_author"]
    user.user_permissions.add(
        *Permission.objects.filter(
            content_type__app_label="authors",
            codename__in=codenames,
        )
    )
    transfer_codenames = []
    if can_import:
        transfer_codenames.append("import_metadata")
    if can_export:
        transfer_codenames.append("export_metadata")
    user.user_permissions.add(
        *Permission.objects.filter(
            content_type__app_label="common",
            codename__in=transfer_codenames,
        )
    )
    return user


def upload(content):
    return SimpleUploadedFile("authors.csv", content.encode(), "text/csv")


def test_workspace_requires_dedicated_permission(client):
    client.force_login(UserFactory(is_staff=True))

    response = client.get(reverse("admin_metadata_transfer"))

    assert response.status_code == 403


def test_author_import_previews_then_requires_explicit_confirmation(client):
    actor = transfer_staff(can_import=True)
    client.force_login(actor)
    content = AUTHOR_HEADER + "laxmi,लक्ष्मी, Laxmi,,,,,Nepal\n"

    preview = client.post(
        reverse("admin_metadata_import_preview"),
        {"import_type": "authors", "csv_file": upload(content)},
    )

    assert preview.status_code == 200
    assert b"Confirm import" in preview.content
    assert not Author.objects.filter(slug="laxmi").exists()
    token = preview.context["token"]

    confirmed = client.post(
        reverse("admin_metadata_import_confirm"),
        {"preview_token": token},
    )

    assert confirmed.status_code == 302
    author = Author.objects.get(slug="laxmi")
    assert author.name_ne == "लक्ष्मी"
    assert AdministrativeAudit.objects.filter(
        staff_user=actor,
        action=AdministrativeAuditAction.METADATA_IMPORTED,
        object_id=str(author.pk),
    ).exists()


def test_dry_run_never_offers_confirmation_or_writes(client):
    actor = transfer_staff(can_import=True)
    client.force_login(actor)
    content = AUTHOR_HEADER + "dry-run,परीक्षण,Test,,,,,Nepal\n"

    response = client.post(
        reverse("admin_metadata_import_preview"),
        {
            "import_type": "authors",
            "csv_file": upload(content),
            "dry_run": "on",
        },
    )

    assert response.status_code == 200
    assert response.context["token"] == ""
    assert b"Dry run" in response.content
    assert not Author.objects.filter(slug="dry-run").exists()


def test_preview_reports_every_invalid_row_and_existing_slug():
    AuthorFactory(slug="existing")
    content = (
        AUTHOR_HEADER + "existing,पहिलो,First,,,,,Nepal\n" + ",दोस्रो,Second,,,,,Nepal\n"
    )

    preview = preview_import("authors", content.encode())

    assert preview.is_valid is False
    assert [error.row for error in preview.errors] == [2, 3]


def test_import_rejects_media_columns(client):
    actor = transfer_staff(can_import=True)
    client.force_login(actor)
    content = AUTHOR_HEADER.strip() + ",image\nnew,नयाँ,New,,,,,Nepal,private.jpg\n"

    response = client.post(
        reverse("admin_metadata_import_preview"),
        {"import_type": "authors", "csv_file": upload(content)},
    )

    assert response.status_code == 200
    assert b"File and media columns are not accepted" in response.content
    assert not Author.objects.filter(slug="new").exists()


def test_author_export_requires_permissions_and_is_audited(client):
    AuthorFactory(slug="exported-author")
    denied = transfer_staff(can_export=False)
    client.force_login(denied)
    url = reverse("admin_metadata_export", kwargs={"kind": "authors"})
    assert client.get(url).status_code == 403
    actor = transfer_staff(can_export=True)
    client.force_login(actor)

    response = client.get(url)

    assert response.status_code == 200
    rows = list(csv.reader(StringIO(response.content.decode())))
    assert "image" not in rows[0]
    assert "exported-author" in response.content.decode()
    assert AdministrativeAudit.objects.filter(
        staff_user=actor,
        action=AdministrativeAuditAction.METADATA_EXPORTED,
        object_type="authors.author",
    ).exists()
