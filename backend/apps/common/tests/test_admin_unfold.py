import pytest
from django.apps import apps
from django.conf import settings
from django.contrib import admin
from django.contrib.auth.models import Permission
from django.contrib.staticfiles import finders
from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse
from unfold.admin import ModelAdmin
from unfold.sites import UnfoldAdminSite

from apps.accounts.models import User
from config.admin import (
    dashboard_callback,
    environment_callback,
    processing_queue_badge,
)


def test_default_admin_site_is_unfold_without_changing_url(client):
    assert isinstance(admin.site, UnfoldAdminSite)
    assert reverse("admin:index") == "/admin/"

    response = client.get(reverse("admin:login"))

    assert response.status_code == 200
    assert b"SunneKatha Administration" in response.content
    assert b"admin/brand/sunnekatha-login.png" in response.content


@pytest.mark.django_db
def test_authenticated_admin_templates_and_custom_user_form_render(client):
    admin_user = User.objects.create_superuser(
        email="admin@example.com",
        username="admin",
        display_name="Admin",
        password="a-secure-test-password",
    )
    client.force_login(admin_user)

    index_response = client.get(reverse("admin:index"))
    user_add_response = client.get(reverse("admin:accounts_user_add"))

    assert index_response.status_code == 200
    assert user_add_response.status_code == 200
    assert settings.UNFOLD["SITE_SUBHEADER"] == "Audio Literature Management"
    assert b"Audio Literature Management" in index_response.content
    assert b"admin/brand/sunnekatha-mark.png" in index_response.content
    assert b'name="email"' in user_add_response.content


def test_custom_user_model_and_project_admin_registrations_are_preserved():
    assert settings.AUTH_USER_MODEL == "accounts.User"
    assert User in admin.site._registry

    project_models = {
        model
        for model in apps.get_models()
        if model._meta.app_config.name.startswith("apps.") and not model._meta.abstract
    }

    assert project_models <= admin.site._registry.keys()
    assert all(
        isinstance(admin.site._registry[model], ModelAdmin) for model in project_models
    )


def test_admin_callbacks_are_safe(rf, monkeypatch):
    request = rf.get("/admin/")
    context = {"existing": "value"}
    monkeypatch.setattr(
        "apps.common.admin_dashboard.build_dashboard_context",
        lambda request: {"dashboard_metrics": []},
    )

    assert environment_callback(request) == ["LOCAL", "success"]
    assert dashboard_callback(request, context) == {
        "existing": "value",
        "dashboard_metrics": [],
    }

    with override_settings(ADMIN_ENVIRONMENT="STAGING"):
        assert environment_callback(request) == ["STAGING", "info"]

    with override_settings(ADMIN_ENVIRONMENT="PRODUCTION"):
        assert environment_callback(request) == ["PRODUCTION", "warning"]


def test_admin_theme_is_warm_and_supports_light_and_dark_modes():
    theme = settings.UNFOLD

    assert theme["SITE_TITLE"] == "SunneKatha Administration"
    assert theme["SITE_HEADER"] == "SunneKatha"
    assert theme["SITE_SUBHEADER"] == "Audio Literature Management"
    assert theme["SITE_SYMBOL"] == "auto_stories"
    assert theme["BORDER_RADIUS"] == "8px"
    assert theme["COLORS"]["base"]["950"] == "oklch(13% .014 35)"
    assert theme["COLORS"]["primary"]["600"] == "oklch(59% .18 43)"
    assert "THEME" not in theme


def test_responsive_admin_styles_are_configured_and_discoverable():
    stylesheet_path = "admin/css/sunnekatha-responsive.css"

    assert finders.find(stylesheet_path)
    assert any(
        stylesheet(None).endswith(stylesheet_path)
        for stylesheet in settings.UNFOLD["STYLES"]
    )


def test_responsive_admin_styles_cover_tablet_interactions():
    stylesheet_path = finders.find("admin/css/sunnekatha-responsive.css")

    with open(stylesheet_path, encoding="utf-8") as stylesheet:
        css = stylesheet.read()

    assert ".formset-wrapper" in css
    assert 'input[name$="-position"]' in css
    assert '[role="dialog"]' in css
    assert ".change-form textarea" in css
    assert "@media (max-width: 48rem)" in css


@pytest.mark.django_db
def test_sidebar_sections_use_named_admin_links_and_remain_collapsible(rf):
    admin_user = User.objects.create_superuser(
        email="sidebar-admin@example.com",
        username="sidebar-admin",
        display_name="Sidebar Admin",
        password="a-secure-test-password",
    )
    request = rf.get("/admin/")
    request.user = admin_user

    sidebar = admin.site.get_sidebar_list(request)

    assert [group["title"] for group in sidebar] == [
        "Dashboard",
        "Content",
        "Editorial",
        "Taxonomy",
        "Audio Operations",
        "Rights",
        "Audience",
        "System",
    ]
    assert all(group["collapsible"] for group in sidebar)
    assert settings.UNFOLD["SIDEBAR"]["show_all_applications"] is True

    items = [item for group in sidebar for item in group["items"]]
    assert all(item["has_permission"] for item in items)
    assert all(
        str(item.get("link_callback", item["link"])).startswith("/admin/")
        for item in items
    )


@pytest.mark.django_db
def test_sidebar_model_permissions_hide_unavailable_items(rf):
    staff_user = User.objects.create_user(
        email="author-editor@example.com",
        username="author-editor",
        display_name="Author Editor",
        password="a-secure-test-password",
        is_staff=True,
    )
    staff_user.user_permissions.add(
        Permission.objects.get(
            content_type__app_label="authors",
            codename="view_author",
        )
    )
    request = rf.get("/admin/")
    request.user = staff_user

    sidebar = admin.site.get_sidebar_list(request)
    items = {item["title"]: item for group in sidebar for item in group["items"]}

    assert items["Authors"]["has_permission"] is True
    assert items["Audio Tracks"]["has_permission"] is False
    assert items["Upload Sessions"]["has_permission"] is False


@pytest.mark.django_db
def test_sidebar_badges_cache_counts_briefly(rf, django_assert_num_queries):
    admin_user = User.objects.create_superuser(
        email="badge-admin@example.com",
        username="badge-admin",
        display_name="Badge Admin",
        password="a-secure-test-password",
    )
    request = rf.get("/admin/")
    request.user = admin_user
    cache.clear()

    with django_assert_num_queries(1):
        assert processing_queue_badge(request) == 0
        assert processing_queue_badge(request) == 0


@pytest.mark.django_db
def test_complete_sidebar_uses_only_five_cached_count_queries(
    rf,
    django_assert_num_queries,
):
    admin_user = User.objects.create_superuser(
        email="query-admin@example.com",
        username="query-admin",
        display_name="Query Admin",
        password="a-secure-test-password",
    )
    request = rf.get("/admin/")
    request.user = admin_user
    cache.clear()

    with django_assert_num_queries(5):
        sidebar = admin.site.get_sidebar_list(request)
        badges = [
            str(item["badge_callback"])
            for group in sidebar
            for item in group["items"]
            if "badge_callback" in item
        ]

    assert badges == ["0", "0", "0", "0", "0"]
