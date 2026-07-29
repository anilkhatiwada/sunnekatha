from datetime import timedelta

import pytest
from django.contrib import admin
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory
from django.urls import reverse
from django.utils import timezone

from apps.accounts.tests.factories import UserFactory
from apps.catalog.admin import (
    CopyrightLicenseAdmin,
    ExpiredPermissionFilter,
    ExpiringSoonFilter,
    MissingDocumentsFilter,
)
from apps.catalog.models import (
    CopyrightLicense,
    CopyrightStatus,
    PermissionDocument,
    PermissionDocumentAudit,
    PermissionDocumentAuditAction,
    RightsHolder,
    RightsPermissionType,
    RightsVerificationStatus,
)
from apps.catalog.rights_services import permission_document_service
from apps.catalog.tests.factories import LiteraryWorkFactory
from apps.common.models import AdministrativeAudit, AdministrativeAuditAction

pytestmark = pytest.mark.django_db


def license_record(**kwargs):
    return CopyrightLicense.objects.create(
        literary_work=kwargs.pop("literary_work", LiteraryWorkFactory()),
        rights_holder=kwargs.pop(
            "rights_holder",
            RightsHolder.objects.create(name="Holder"),
        ),
        permission_type=kwargs.pop(
            "permission_type",
            RightsPermissionType.AUDIO_COMMERCIAL,
        ),
        **kwargs,
    )


def rights_staff(*codenames):
    user = UserFactory(is_staff=True)
    user.user_permissions.add(
        *Permission.objects.filter(
            content_type__app_label="catalog",
            codename__in=codenames,
        )
    )
    return user.__class__.objects.get(pk=user.pk)


def document_record(**kwargs):
    return PermissionDocument.objects.create(
        license=kwargs.pop("license", license_record()),
        title=kwargs.pop("title", "Human-readable permission name"),
        document=kwargs.pop(
            "document",
            "originals/permission-documents/permissiondocument/test/document.pdf",
        ),
        **kwargs,
    )


def test_license_rejects_expiration_before_effective_date():
    record = CopyrightLicense(
        literary_work=LiteraryWorkFactory(),
        permission_type=RightsPermissionType.AUDIO,
        effective_date=timezone.localdate(),
        expiration_date=timezone.localdate() - timedelta(days=1),
    )

    with pytest.raises(ValidationError, match="Expiration"):
        record.full_clean()


def test_rights_admin_displays_requested_columns_and_filters():
    model_admin = admin.site._registry[CopyrightLicense]

    assert isinstance(model_admin, CopyrightLicenseAdmin)
    assert model_admin.list_display == (
        "literary_work",
        "copyright_status",
        "rights_holder",
        "permission_type",
        "effective_date",
        "expiration_date",
        "territory",
        "allows_monetization",
        "allows_audio",
        "document_availability",
        "verification_status",
        "date_warning",
    )
    assert ExpiringSoonFilter in model_admin.list_filter
    assert ExpiredPermissionFilter in model_admin.list_filter
    assert MissingDocumentsFilter in model_admin.list_filter
    assert "publish_selected" not in model_admin.actions


def test_rights_filters_and_search_are_available_in_admin(client):
    user = UserFactory(is_staff=True, is_superuser=True)
    work = LiteraryWorkFactory(
        title_ne="अधिकार परीक्षण",
        copyright_status=CopyrightStatus.PERMISSION_GRANTED,
    )
    expiring = license_record(
        literary_work=work,
        expiration_date=timezone.localdate() + timedelta(days=10),
        verification_status=RightsVerificationStatus.VERIFIED,
    )
    license_record(expiration_date=timezone.localdate() - timedelta(days=2))
    client.force_login(user)

    response = client.get(
        reverse("admin:catalog_copyrightlicense_changelist"),
        {
            "expiring_soon": "yes",
            "missing_documents": "yes",
            "literary_work__copyright_status": CopyrightStatus.PERMISSION_GRANTED,
            "q": "अधिकार परीक्षण",
        },
    )

    assert response.status_code == 200
    assert list(response.context["cl"].queryset) == [expiring]


def test_document_availability_uses_stored_documents_without_exposing_content():
    record = license_record()
    document = PermissionDocument.objects.create(
        license=record,
        title="Signed permission",
        document=SimpleUploadedFile(
            "permission.pdf",
            b"%PDF-1.4 stored test document",
            content_type="application/pdf",
        ),
    )
    model_admin = admin.site._registry[CopyrightLicense]
    annotated = model_admin.get_queryset(
        type("Request", (), {"user": UserFactory(is_superuser=True)})()
    ).get(pk=record.pk)

    assert model_admin.document_availability(annotated) == "1 document(s)"
    assert document.document.name.startswith("originals/permission-documents/")


def test_change_page_states_that_records_are_not_legal_determinations(client):
    user = UserFactory(is_staff=True, is_superuser=True)
    record = license_record()
    client.force_login(user)

    response = client.get(
        reverse("admin:catalog_copyrightlicense_change", args=(record.pk,))
    )

    assert response.status_code == 200
    assert b"does not determine legal validity" in response.content


def test_document_admin_displays_metadata_without_private_storage_url(client):
    user = UserFactory(is_staff=True, is_superuser=True)
    document = document_record(uploaded_by=user, notes="Stored editorial note")
    client.force_login(user)

    response = client.get(
        reverse("admin:catalog_permissiondocument_change", args=(document.pk,))
    )
    content = response.content.decode()

    assert response.status_code == 200
    assert document.title in content
    assert "Download securely" in content
    assert "Preview securely" in content
    assert document.document.name not in content
    assert "amazonaws.com" not in content


def test_secure_download_requires_permission_and_audits_access(client, monkeypatch):
    document = document_record()
    ordinary_staff = UserFactory(is_staff=True)
    authorized = rights_staff("view_permissiondocument")
    delivery = {
        "url": "https://media.example.com/restricted/document.pdf?Signature=signed",
        "expiresAt": timezone.now() + timedelta(minutes=2),
    }
    calls = []

    def deliver(**kwargs):
        calls.append(kwargs)
        return delivery

    monkeypatch.setattr(
        "apps.catalog.admin.cloudfront_media_service.deliver_admin_document",
        deliver,
    )
    url = reverse(
        "admin:catalog_permissiondocument_secure",
        args=(document.pk, "download"),
    )

    client.force_login(ordinary_staff)
    denied = client.get(url)
    client.force_login(authorized)
    allowed = client.get(url)

    assert denied.status_code == 403
    assert allowed.status_code == 302
    assert allowed["Location"] == delivery["url"]
    cache_control = allowed["Cache-Control"]
    assert "private" in cache_control
    assert "no-store" in cache_control
    assert calls[0]["object_key"] == document.document.name
    audit = PermissionDocumentAudit.objects.get(document=document)
    assert audit.action == PermissionDocumentAuditAction.DOWNLOADED
    assert audit.actor == authorized


def test_verify_and_revoke_actions_are_permission_checked_and_audited():
    document = document_record()
    unauthorized = UserFactory(is_staff=True)
    verifier = rights_staff("verify_permissiondocument")
    queryset = PermissionDocument.objects.filter(pk=document.pk)

    with pytest.raises(PermissionDenied) as exc:
        permission_document_service.verify(
            queryset=queryset,
            actor=unauthorized,
        )
    assert "permission" in str(exc.value).lower()

    assert permission_document_service.verify(queryset=queryset, actor=verifier) == 1
    document.refresh_from_db()
    assert document.is_verified is True
    assert document.verified_by == verifier
    assert document.verified_at is not None

    assert (
        permission_document_service.revoke_verification(
            queryset=queryset,
            actor=verifier,
        )
        == 1
    )
    document.refresh_from_db()
    assert document.is_verified is False
    assert document.verified_by is None
    assert list(document.audit_events.values_list("action", flat=True)) == [
        PermissionDocumentAuditAction.VERIFICATION_REVOKED,
        PermissionDocumentAuditAction.VERIFIED,
    ]
    assert set(
        AdministrativeAudit.objects.filter(object_id=str(document.pk)).values_list(
            "action",
            flat=True,
        )
    ) == {
        AdministrativeAuditAction.COPYRIGHT_VERIFIED,
        AdministrativeAuditAction.COPYRIGHT_REVOKED,
    }


def test_document_expiry_warning_and_safe_preview_rules():
    expiring = document_record()
    expiring.license.expiration_date = timezone.localdate() + timedelta(days=5)
    expiring.license.save(update_fields=("expiration_date", "updated_at"))
    unsafe = document_record(document="originals/permission-documents/test/unsafe.txt")
    model_admin = admin.site._registry[PermissionDocument]

    assert model_admin.expiry_warning(expiring) == ("expiring", "Expires in 5 days")
    assert "unavailable" in str(model_admin.safe_preview(unsafe)).lower()


def test_new_document_records_uploader_in_admin_save():
    uploader = rights_staff("add_permissiondocument")
    request = RequestFactory().post("/admin/catalog/permissiondocument/add/")
    request.user = uploader
    document = document_record()
    document.uploaded_by = None
    model_admin = admin.site._registry[PermissionDocument]

    model_admin.save_model(request, document, form=None, change=False)

    document.refresh_from_db()
    assert document.uploaded_by == uploader
