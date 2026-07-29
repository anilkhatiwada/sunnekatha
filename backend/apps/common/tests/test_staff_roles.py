from io import StringIO

import pytest
from django.contrib.auth.models import Group, Permission
from django.core.management import call_command
from django.urls import reverse

from apps.accounts.tests.factories import UserFactory
from apps.common.staff_roles import ROLE_NAMES, ROLE_PERMISSIONS

pytestmark = pytest.mark.django_db


@pytest.fixture
def configured_roles():
    call_command("setup_staff_roles", stdout=StringIO())
    return {group.name: group for group in Group.objects.filter(name__in=ROLE_NAMES)}


def role_user(configured_roles, role):
    user = UserFactory(is_staff=True)
    user.groups.add(configured_roles[role])
    return user


def test_setup_staff_roles_is_idempotent_and_preserves_custom_permissions():
    call_command("setup_staff_roles", stdout=StringIO())
    analytics = Group.objects.get(name="Analytics Viewer")
    custom = Permission.objects.get(
        content_type__app_label="accounts",
        codename="delete_user",
    )
    analytics.permissions.add(custom)

    call_command("setup_staff_roles", stdout=StringIO())

    assert set(
        Group.objects.filter(name__in=ROLE_NAMES).values_list("name", flat=True)
    ) == set(ROLE_NAMES)
    analytics.refresh_from_db()
    assert custom in analytics.permissions.all()


@pytest.mark.parametrize(
    ("role", "allowed", "denied"),
    (
        (
            "Publisher",
            ("catalog.approve_audiotrack", "catalog.publish_audiotrack"),
            ("catalog.retry_audioprocessingjob", "accounts.change_user"),
        ),
        (
            "Senior Editor",
            ("catalog.approve_audiotrack", "catalog.change_audiotrack"),
            ("catalog.publish_audiotrack", "accounts.change_user"),
        ),
        (
            "Editor",
            ("catalog.change_audiotrack", "home.change_homesection"),
            ("catalog.approve_audiotrack", "catalog.publish_audiotrack"),
        ),
        (
            "Audio Manager",
            ("catalog.retry_audioprocessingjob", "uploads.change_uploadsession"),
            ("catalog.approve_audiotrack", "playlists.change_playlist"),
        ),
        (
            "Playlist Curator",
            ("playlists.change_playlist", "catalog.view_audiotrack"),
            ("catalog.publish_audiotrack", "home.change_homesection"),
        ),
        (
            "Copyright Manager",
            (
                "catalog.change_copyrightlicense",
                "catalog.verify_permissiondocument",
            ),
            ("catalog.publish_audiotrack", "accounts.change_user"),
        ),
        (
            "Support Staff",
            ("accounts.change_user", "subscriptions.change_usersubscription"),
            ("catalog.change_audiotrack", "analytics.view_dailyplatformmetric"),
        ),
        (
            "Analytics Viewer",
            (
                "analytics.view_dailyplatformmetric",
                "analytics.view_dailytrackmetric",
            ),
            ("accounts.view_user", "catalog.view_audiotrack"),
        ),
    ),
)
def test_role_permission_boundaries(configured_roles, role, allowed, denied):
    user = role_user(configured_roles, role)

    assert all(user.has_perm(permission) for permission in allowed)
    assert not any(user.has_perm(permission) for permission in denied)


def test_super_administrator_contains_every_managed_permission(configured_roles):
    user = role_user(configured_roles, "Super Administrator")

    assert all(
        user.has_perm(permission)
        for permission in ROLE_PERMISSIONS["Super Administrator"]
    )


@pytest.mark.parametrize(
    ("role", "allowed_url", "denied_url"),
    (
        (
            "Analytics Viewer",
            "admin:analytics_dailyplatformmetric_changelist",
            "admin:accounts_user_changelist",
        ),
        (
            "Playlist Curator",
            "admin:playlists_playlist_changelist",
            "admin:home_homesection_changelist",
        ),
        (
            "Copyright Manager",
            "admin:catalog_permissiondocument_changelist",
            "admin:accounts_user_changelist",
        ),
        (
            "Support Staff",
            "admin:accounts_user_changelist",
            "admin:catalog_audiotrack_changelist",
        ),
    ),
)
def test_roles_can_access_only_representative_admin_pages(
    client,
    configured_roles,
    role,
    allowed_url,
    denied_url,
):
    client.force_login(role_user(configured_roles, role))

    allowed = client.get(reverse(allowed_url))
    denied = client.get(reverse(denied_url))

    assert allowed.status_code == 200
    assert denied.status_code == 403
