from urllib.parse import urlencode

from django.contrib import admin
from django.db.models import Count, Exists, OuterRef, Q
from django.urls import reverse
from django.utils.html import format_html, format_html_join
from unfold.admin import ModelAdmin
from unfold.contrib.filters.admin import BooleanRadioFilter, ChoicesDropdownFilter

from apps.authors.models import Author
from apps.authors.services import author_editorial_service
from apps.catalog.models import CopyrightStatus, LiteraryWork
from apps.common.admin import ImagePreviewAdminMixin, ProtectedDeleteAdminMixin
from apps.common.admin_performance import (
    is_admin_autocomplete_request,
    is_admin_changelist_request,
)
from apps.common.admin_search import RomanizedAliasAdminSearchMixin
from apps.search.models import SearchEntityType


class HasPublishedContentFilter(admin.SimpleListFilter):
    title = "published content"
    parameter_name = "has_published_content"

    def lookups(self, request, model_admin):
        return (("yes", "Has published content"), ("no", "No published content"))

    def queryset(self, request, queryset):
        published = LiteraryWork.objects.filter(
            author_id=OuterRef("pk"),
        ).filter(Q(is_published=True) | Q(audio_tracks__is_published=True))
        queryset = queryset.annotate(_has_published_content=Exists(published))
        if self.value() == "yes":
            return queryset.filter(_has_published_content=True)
        if self.value() == "no":
            return queryset.filter(_has_published_content=False)
        return queryset


class HasCopyrightIssuesFilter(admin.SimpleListFilter):
    title = "copyright issues"
    parameter_name = "has_copyright_issues"

    def lookups(self, request, model_admin):
        return (("yes", "Has unresolved issues"), ("no", "No unresolved issues"))

    def queryset(self, request, queryset):
        unresolved = LiteraryWork.objects.filter(
            author_id=OuterRef("pk"),
            copyright_status=CopyrightStatus.UNKNOWN,
        )
        queryset = queryset.annotate(_has_copyright_issues=Exists(unresolved))
        if self.value() == "yes":
            return queryset.filter(_has_copyright_issues=True)
        if self.value() == "no":
            return queryset.filter(_has_copyright_issues=False)
        return queryset


@admin.register(Author)
class AuthorAdmin(
    RomanizedAliasAdminSearchMixin,
    ProtectedDeleteAdminMixin,
    ImagePreviewAdminMixin,
    ModelAdmin,
):
    list_display = (
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
    list_filter = (
        ("is_featured", BooleanRadioFilter),
        ("is_verified", BooleanRadioFilter),
        ("country", ChoicesDropdownFilter),
        HasPublishedContentFilter,
        HasCopyrightIssuesFilter,
    )
    search_fields = (
        "=id",
        "slug",
        "name_ne",
        "name_en",
        "biography_ne",
        "biography_en",
        "country",
    )
    search_alias_mappings = ((SearchEntityType.AUTHOR, "id"),)
    readonly_fields = (
        "id",
        "slug",
        "image_preview",
        "related_literary_works",
        "related_audio_tracks",
        "public_profile_preview",
        "duplicate_name_warning",
        "created_at",
        "updated_at",
    )
    actions = ("feature_selected", "unfeature_selected", "verify_selected")
    fieldsets = (
        (
            "Identity",
            {
                "fields": (
                    "name_ne",
                    "name_en",
                    "slug",
                    "duplicate_name_warning",
                )
            },
        ),
        (
            "Biography",
            {"fields": ("biography_ne", "biography_en")},
        ),
        (
            "Image",
            {"fields": ("image", "image_preview")},
        ),
        (
            "Life Information",
            {"fields": ("birth_date", "death_date", "country")},
        ),
        (
            "Editorial Status",
            {
                "fields": (
                    "is_featured",
                    "is_verified",
                    "public_profile_preview",
                )
            },
        ),
        (
            "Related Content",
            {"fields": ("related_literary_works", "related_audio_tracks")},
        ),
        (
            "System Information",
            {
                "classes": ("collapse",),
                "fields": ("id", "created_at", "updated_at"),
            },
        ),
    )

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if is_admin_autocomplete_request(request):
            return queryset.only("id", "slug", "name_ne", "name_en")
        queryset = queryset.annotate(
            _work_count=Count("literary_works", distinct=True),
            _track_count=Count(
                "literary_works__audio_tracks",
                distinct=True,
            ),
            _copyright_issue_count=Count(
                "literary_works",
                filter=Q(literary_works__copyright_status=CopyrightStatus.UNKNOWN),
                distinct=True,
            ),
        )
        if is_admin_changelist_request(request):
            queryset = queryset.defer("biography_ne", "biography_en")
        return queryset

    @admin.display(description="Works", ordering="_work_count")
    def work_count(self, obj):
        return obj._work_count

    @admin.display(description="Tracks", ordering="_track_count")
    def track_count(self, obj):
        return obj._track_count

    @admin.display(
        description="Copyright issues",
        ordering="_copyright_issue_count",
    )
    def copyright_issue_count(self, obj):
        return obj._copyright_issue_count

    @staticmethod
    def _admin_list_link(url_name, label, **filters):
        url = reverse(url_name)
        if filters:
            url = f"{url}?{urlencode(filters)}"
        return format_html('<a href="{}">{}</a>', url, label)

    @admin.display(description="Literary works")
    def related_literary_works(self, obj):
        if not obj:
            return "Available after the author is saved."
        count = obj.literary_works.count()
        return self._admin_list_link(
            "admin:catalog_literarywork_changelist",
            f"Open {count} related literary work(s) ↗",
            author__id__exact=obj.pk,
        )

    @admin.display(description="Audio tracks")
    def related_audio_tracks(self, obj):
        if not obj:
            return "Available after the author is saved."
        count = obj.literary_works.aggregate(
            count=Count("audio_tracks", distinct=True)
        )["count"]
        return self._admin_list_link(
            "admin:catalog_audiotrack_changelist",
            f"Open {count} related audio track(s) ↗",
            work__author__id__exact=obj.pk,
        )

    @admin.display(description="Public profile")
    def public_profile_preview(self, obj):
        if not obj or not obj.slug:
            return "Available after the author is saved."
        return format_html(
            '<a href="{}" target="_blank" rel="noopener">Preview public profile ↗</a>',
            reverse("authors:detail", kwargs={"slug": obj.slug}),
        )

    def get_view_on_site_url(self, obj=None):
        if obj is None or not obj.slug:
            return None
        return reverse("authors:detail", kwargs={"slug": obj.slug})

    def _similar_authors(self, obj):
        if not obj:
            return Author.objects.none()
        query = Q()
        if obj.name_ne.strip():
            query |= Q(name_ne__iexact=obj.name_ne.strip())
            if len(obj.name_ne.strip()) >= 3:
                query |= Q(name_ne__icontains=obj.name_ne.strip())
        if obj.name_en.strip():
            query |= Q(name_en__iexact=obj.name_en.strip())
            if len(obj.name_en.strip()) >= 3:
                query |= Q(name_en__icontains=obj.name_en.strip())
        if not query:
            return Author.objects.none()
        return (
            Author.objects.filter(query)
            .exclude(pk=obj.pk)
            .order_by("name_ne", "id")[:5]
        )

    @admin.display(description="Possible duplicate authors")
    def duplicate_name_warning(self, obj):
        similar = list(self._similar_authors(obj))
        if not similar:
            return "No similar saved author names detected."
        links = format_html_join(
            ", ",
            '<a href="{}">{}</a>',
            (
                (
                    reverse("admin:authors_author_change", args=(author.pk,)),
                    f"{author.name_ne} / {author.name_en}".rstrip(" /"),
                )
                for author in similar
            ),
        )
        return format_html(
            '<div class="messagelist warning">Review possible duplicates: {}</div>',
            links,
        )

    @admin.action(description="Feature selected authors")
    def feature_selected(self, request, queryset):
        result = author_editorial_service.set_featured(
            queryset,
            value=True,
            actor=request.user,
        )
        self.message_user(request, f"Featured {result.updated} author(s).")

    @admin.action(description="Remove selected authors from featured")
    def unfeature_selected(self, request, queryset):
        result = author_editorial_service.set_featured(
            queryset,
            value=False,
            actor=request.user,
        )
        self.message_user(request, f"Unfeatured {result.updated} author(s).")

    @admin.action(description="Verify selected authors")
    def verify_selected(self, request, queryset):
        result = author_editorial_service.set_verified(
            queryset,
            actor=request.user,
        )
        self.message_user(request, f"Verified {result.updated} author(s).")
