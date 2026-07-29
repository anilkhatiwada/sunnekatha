"""Root URL configuration."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from apps.common.metadata_transfer_views import (
    metadata_export_view,
    metadata_import_confirm_view,
    metadata_import_preview_view,
    metadata_transfer_view,
)

urlpatterns = [
    path(
        "admin/metadata-transfer/",
        admin.site.admin_view(metadata_transfer_view),
        name="admin_metadata_transfer",
    ),
    path(
        "admin/metadata-transfer/export/<str:kind>/",
        admin.site.admin_view(metadata_export_view),
        name="admin_metadata_export",
    ),
    path(
        "admin/metadata-transfer/import/preview/",
        admin.site.admin_view(metadata_import_preview_view),
        name="admin_metadata_import_preview",
    ),
    path(
        "admin/metadata-transfer/import/confirm/",
        admin.site.admin_view(metadata_import_confirm_view),
        name="admin_metadata_import_confirm",
    ),
    path("admin/", admin.site.urls),
    path("api/v1/", include("apps.common.urls")),
    path("api/v1/staff/analytics/", include("apps.analytics.urls")),
    path("api/v1/creator/", include("apps.creators.urls")),
    path("api/v1/", include("apps.explore.urls")),
    path("api/v1/", include("apps.home.urls")),
    path("api/v1/auth/", include("apps.accounts.urls")),
    path("api/v1/authors/", include("apps.authors.urls")),
    path("api/v1/library/", include("apps.library.urls")),
    path("api/v1/me/", include("apps.library.progress_urls")),
    path("api/v1/narrators/", include("apps.narrators.urls")),
    path("api/v1/notifications/", include("apps.notifications.urls")),
    path("api/v1/playlists/", include("apps.playlists.urls")),
    path("api/v1/search/", include("apps.search.urls")),
    path("api/v1/uploads/", include("apps.uploads.urls")),
    path("api/v1/", include("apps.catalog.urls")),
    path("api/v1/", include("apps.taxonomy.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
