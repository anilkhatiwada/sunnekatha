import pytest
from django.contrib import admin
from django.contrib.auth.models import Group, Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import RequestFactory
from django.urls import reverse

from apps.accounts.admin import SunneKathaUserAdmin
from apps.accounts.models import User
from apps.accounts.services import account_status_service
from apps.accounts.tests.factories import UserFactory
from apps.subscriptions.tests.factories import UserSubscriptionFactory

pytestmark = pytest.mark.django_db


def staff_with_user_permissions(*codenames):
    user = UserFactory(is_staff=True)
    user.user_permissions.add(
        *Permission.objects.filter(
            content_type__app_label="accounts",
            codename__in=codenames,
        )
    )
    return user


def test_user_changelist_shows_requested_columns_and_premium_filter(client):
    staff = staff_with_user_permissions("view_user", "change_user")
    premium_user = UserSubscriptionFactory().user
    client.force_login(staff)

    response = client.get(reverse("admin:accounts_user_changelist"))
    filtered = client.get(
        reverse("admin:accounts_user_changelist"),
        {"premium": "yes"},
    )

    assert response.status_code == 200
    content = response.content.decode()
    for heading in (
        "Email",
        "Display name",
        "Account type",
        "Staff",
        "Creator",
        "Premium",
        "Active",
        "Date joined",
        "Last login",
    ):
        assert heading in content
    assert filtered.status_code == 200
    assert premium_user.email in filtered.content.decode()


def test_user_change_page_has_related_links_without_password_hash(client):
    staff = staff_with_user_permissions("view_user", "change_user")
    user = UserFactory(creator=True)
    client.force_login(staff)

    response = client.get(reverse("admin:accounts_user_change", args=(user.pk,)))

    assert response.status_code == 200
    content = response.content.decode()
    for section in (
        "Identity",
        "Account Status",
        "User Preferences",
        "Roles and Permissions",
        "Subscription",
        "Activity Summary",
        "Security Metadata",
    ):
        assert section in content
    assert "View subscriptions" in content
    assert "Listening progress" in content
    assert "Change password securely" in content
    assert user.password not in content
    assert "refresh token" not in content.lower()
    assert "access token" not in content.lower()


def test_account_status_service_suspends_and_reactivates():
    actor = staff_with_user_permissions("change_user")
    user = UserFactory()

    account_status_service.suspend(actor=actor, user=user)
    user.refresh_from_db()
    assert not user.is_active

    account_status_service.reactivate(actor=actor, user=user)
    user.refresh_from_db()
    assert user.is_active


def test_account_status_service_rejects_self_suspension():
    actor = staff_with_user_permissions("change_user")

    with pytest.raises(ValidationError, match="own account"):
        account_status_service.suspend(actor=actor, user=actor)


def test_non_superuser_cannot_modify_or_suspend_superuser(client):
    staff = staff_with_user_permissions("view_user", "change_user")
    superuser = UserFactory(is_staff=True, is_superuser=True)
    client.force_login(staff)

    response = client.get(reverse("admin:accounts_user_change", args=(superuser.pk,)))

    assert response.status_code == 200
    assert 'name="_save"' not in response.content.decode()
    with pytest.raises(PermissionDenied, match="Only a superuser"):
        account_status_service.suspend(actor=staff, user=superuser)


def test_non_superuser_cannot_grant_superuser_status():
    staff = staff_with_user_permissions("change_user")
    target = UserFactory(is_superuser=True)
    request = RequestFactory().post("/")
    request.user = staff
    model_admin = SunneKathaUserAdmin(User, admin.site)

    with pytest.raises(PermissionDenied, match="Only a superuser"):
        model_admin.save_model(request, target, form=None, change=True)


def test_non_superuser_cannot_edit_staff_roles_or_direct_permissions(client):
    staff = staff_with_user_permissions("view_user", "change_user")
    client.force_login(staff)

    response = client.get(reverse("admin:accounts_user_change", args=(staff.pk,)))
    content = response.content.decode()

    assert response.status_code == 200
    assert 'name="is_staff"' not in content
    assert 'name="is_superuser"' not in content
    assert 'name="groups"' not in content
    assert 'name="user_permissions"' not in content


def test_non_superuser_save_guard_rejects_staff_elevation():
    staff = staff_with_user_permissions("change_user")
    target = UserFactory()
    target.is_staff = True
    request = RequestFactory().post("/")
    request.user = staff
    model_admin = SunneKathaUserAdmin(User, admin.site)

    with pytest.raises(PermissionDenied, match="administrative access"):
        model_admin.save_model(request, target, form=None, change=True)

    target.refresh_from_db()
    assert target.is_staff is False


def test_suspend_admin_action_requires_confirmation(client):
    staff = staff_with_user_permissions("view_user", "change_user")
    target = UserFactory()
    client.force_login(staff)

    response = client.post(
        reverse("admin:accounts_user_changelist"),
        {
            "action": "suspend_accounts",
            "_selected_action": str(target.pk),
        },
    )

    assert response.status_code == 200
    assert b"Suspend selected accounts" in response.content
    target.refresh_from_db()
    assert target.is_active is True


def test_non_superuser_cannot_mutate_group_permissions(rf):
    staff = UserFactory(is_staff=True)
    staff.user_permissions.add(
        Permission.objects.get(
            content_type__app_label="auth",
            codename="change_group",
        )
    )
    request = rf.get("/")
    request.user = staff
    group_admin = admin.site._registry[Group]

    assert group_admin.has_add_permission(request) is False
    assert group_admin.has_change_permission(request, Group(name="Editors")) is False
    assert group_admin.has_delete_permission(request, Group(name="Editors")) is False
