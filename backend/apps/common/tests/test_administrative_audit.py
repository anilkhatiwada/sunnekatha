from types import SimpleNamespace

import pytest
from django.contrib import admin
from django.contrib.auth.models import Permission
from django.urls import reverse

from apps.accounts.services import account_status_service
from apps.accounts.tests.factories import UserFactory
from apps.catalog.admin import LiteraryWorkAdmin
from apps.catalog.models import LiteraryWork
from apps.catalog.tests.factories import LiteraryWorkFactory
from apps.common.audit import administrative_audit_service
from apps.common.models import AdministrativeAudit, AdministrativeAuditAction

pytestmark = pytest.mark.django_db


def audit_viewer():
    user = UserFactory(is_staff=True)
    user.user_permissions.add(
        Permission.objects.get(
            content_type__app_label="common",
            codename="view_administrativeaudit",
        )
    )
    return user


def user_manager():
    user = UserFactory(is_staff=True)
    user.user_permissions.add(
        Permission.objects.get(
            content_type__app_label="accounts",
            codename="change_user",
        )
    )
    return user


def test_audit_service_redacts_sensitive_values_and_reason(rf):
    actor = UserFactory(is_staff=True)
    work = LiteraryWorkFactory()
    request = rf.get("/", HTTP_X_REQUEST_ID="admin-request-123")
    request.user = actor

    audit = administrative_audit_service.record(
        actor=actor,
        action=AdministrativeAuditAction.EDITED,
        obj=work,
        reason=(
            "token=secret-value password=hunter2 "
            "https://signed.example/media?Signature=private"
        ),
        before={
            "title_ne": "Before",
            "password": "hash",
            "access_token": "jwt",
            "audio_master_file": "private/key.mp3",
            "transcript": "private words",
        },
        after={"title_ne": "After", "status": "draft"},
        request_identifier=request.headers["X-Request-ID"],
    )

    assert audit.before_summary == {"title_ne": "Before"}
    assert audit.after_summary == {"title_ne": "After", "status": "draft"}
    assert "secret-value" not in audit.reason
    assert "hunter2" not in audit.reason
    assert "signed.example" not in audit.reason
    assert audit.request_identifier == "admin-request-123"


def test_protected_admin_mixin_records_allowlisted_content_edit(rf):
    actor = UserFactory(is_staff=True, is_superuser=True)
    work = LiteraryWorkFactory(title_ne="अघिल्लो शीर्षक")
    work.title_ne = "नयाँ शीर्षक"
    request = rf.post("/", HTTP_X_REQUEST_ID="edit-456")
    request.user = actor
    request.request_identifier = "edit-456"
    form = SimpleNamespace(
        changed_data=["title_ne", "description_ne"],
        initial={
            "title_ne": "अघिल्लो शीर्षक",
            "description_ne": "Sensitive long content",
        },
    )
    model_admin = LiteraryWorkAdmin(LiteraryWork, admin.site)

    model_admin.save_model(request, work, form, change=True)

    audit = AdministrativeAudit.objects.get(
        action=AdministrativeAuditAction.EDITED,
        object_id=str(work.pk),
    )
    assert audit.staff_user == actor
    assert audit.before_summary == {"title_ne": "अघिल्लो शीर्षक"}
    assert audit.after_summary == {"title_ne": "नयाँ शीर्षक"}
    assert audit.request_identifier == "edit-456"


def test_protected_admin_mixin_records_content_creation(rf):
    actor = UserFactory(is_staff=True, is_superuser=True)
    existing_work = LiteraryWorkFactory()
    work = LiteraryWorkFactory.build(
        author=existing_work.author,
        language=existing_work.language,
        is_published=False,
        published_at=None,
    )
    request = rf.post("/")
    request.user = actor
    form = SimpleNamespace(changed_data=[], initial={})

    LiteraryWorkAdmin(LiteraryWork, admin.site).save_model(
        request,
        work,
        form,
        change=False,
    )

    assert AdministrativeAudit.objects.filter(
        action=AdministrativeAuditAction.CREATED,
        object_id=str(work.pk),
        staff_user=actor,
    ).exists()


def test_user_suspension_records_semantic_audit_event():
    actor = user_manager()
    target = UserFactory()

    account_status_service.suspend(actor=actor, user=target)

    audit = AdministrativeAudit.objects.get(
        action=AdministrativeAuditAction.USER_SUSPENDED,
        object_id=str(target.pk),
    )
    assert audit.staff_user == actor
    assert audit.before_summary == {"is_active": True}
    assert audit.after_summary == {"is_active": False}


def test_request_identifier_middleware_returns_sanitized_identifier(client):
    response = client.get(
        reverse("common:health"),
        HTTP_X_REQUEST_ID="request id/unsafe",
    )

    assert response["X-Request-ID"] == "request-id-unsafe"


def test_audit_admin_requires_dedicated_permission_and_is_read_only(client):
    audit = administrative_audit_service.record(
        actor=UserFactory(is_staff=True),
        action=AdministrativeAuditAction.CREATED,
        obj=LiteraryWorkFactory(),
        reason="Created through editorial admin.",
    )
    unauthorized = UserFactory(is_staff=True)
    client.force_login(unauthorized)
    denied = client.get(reverse("admin:common_administrativeaudit_changelist"))
    client.force_login(audit_viewer())
    allowed = client.get(reverse("admin:common_administrativeaudit_changelist"))
    change = client.get(
        reverse("admin:common_administrativeaudit_change", args=(audit.pk,))
    )

    assert denied.status_code == 403
    assert allowed.status_code == 200
    assert change.status_code == 200
    assert 'name="_save"' not in change.content.decode()
