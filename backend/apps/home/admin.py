from django import forms
from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.db.models import Count
from django.forms.models import BaseInlineFormSet
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import display

from apps.common.admin import ProtectedDeleteAdminMixin
from apps.common.admin_actions import confirm_bulk_action
from apps.home.editorial_services import (
    HomeSectionItemInput,
    home_editorial_service,
)
from apps.home.models import HomeSection, HomeSectionItem


class HomeSectionItemAdminForm(forms.ModelForm):
    class Meta:
        model = HomeSectionItem
        fields = (
            "position",
            "track",
            "playlist",
            "album",
            "author",
            "narrator",
            "genre",
            "mood",
        )

    def _get_validation_exclusions(self):
        exclusions = super()._get_validation_exclusions()
        # Position swaps are validated across the complete formset and applied
        # atomically by HomeEditorialService.
        exclusions.add("position")
        return exclusions


class HomeSectionItemAdminFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return
        active_forms = [
            form
            for form in self.forms
            if form.cleaned_data and not form.cleaned_data.get("DELETE")
        ]
        positions = [form.cleaned_data["position"] for form in active_forms]
        if len(positions) != len(set(positions)):
            raise ValidationError(
                "Each homepage item must have a unique integer position."
            )
        allowed = HomeSectionItem.SECTION_TARGETS[self.instance.section_type]
        for form in active_forms:
            selected = {
                field
                for field in HomeSectionItem.TARGET_FIELDS
                if form.cleaned_data.get(field) is not None
            }
            if len(selected) != 1:
                raise ValidationError(
                    "Select exactly one linked content item on every row."
                )
            if not selected.issubset(allowed):
                raise ValidationError(
                    "Linked content must match the selected section type."
                )

    def save(self, commit=True):
        if not commit:
            raise ValueError("Homepage item changes require an atomic service save.")
        desired = []
        for index, form in enumerate(self.forms):
            if not form.cleaned_data or form.cleaned_data.get("DELETE"):
                continue
            selected = next(
                field
                for field in HomeSectionItem.TARGET_FIELDS
                if form.cleaned_data.get(field) is not None
            )
            target = form.cleaned_data[selected]
            desired.append(
                (
                    form.cleaned_data["position"],
                    index,
                    HomeSectionItemInput(
                        item_id=(
                            form.instance.pk
                            if form.instance._state.adding is False
                            else None
                        ),
                        target_field=selected,
                        target_id=target.pk,
                    ),
                )
            )
        desired.sort(key=lambda row: (row[0], row[1]))
        saved = home_editorial_service.replace_items(
            section=self.instance,
            items=[row[2] for row in desired],
            actor=getattr(self, "admin_user", None),
        )
        self.new_objects = []
        self.changed_objects = []
        self.deleted_objects = []
        return saved


class HomeSectionItemInline(TabularInline):
    model = HomeSectionItem
    extra = 1
    ordering = ("position",)
    ordering_field = "position"
    hide_ordering_field = False
    form = HomeSectionItemAdminForm
    formset = HomeSectionItemAdminFormSet
    autocomplete_fields = (
        "track",
        "playlist",
        "album",
        "author",
        "narrator",
        "genre",
        "mood",
    )
    fields = (
        "position",
        "track",
        "playlist",
        "album",
        "author",
        "narrator",
        "genre",
        "mood",
        "linked_content_preview",
    )
    readonly_fields = ("linked_content_preview",)

    def get_formset(self, request, obj=None, **kwargs):
        base_formset = super().get_formset(request, obj, **kwargs)
        user = request.user

        class RequestHomeSectionItemFormSet(base_formset):
            admin_user = user

        return RequestHomeSectionItemFormSet

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related(
                "track",
                "playlist",
                "album",
                "author",
                "narrator",
                "genre",
                "mood",
            )
        )

    @admin.display(description="Preview")
    def linked_content_preview(self, obj):
        return linked_content_admin_link(obj)


@admin.register(HomeSection)
class HomeSectionAdmin(ProtectedDeleteAdminMixin, ModelAdmin):
    list_display = (
        "sort_order",
        "identifier",
        "title_ne",
        "title_en",
        "section_type",
        "layout",
        "max_items",
        "schedule_badge",
        "item_count",
        "starts_at",
        "ends_at",
        "homepage_preview",
    )
    list_editable = ("sort_order",)
    list_display_links = ("identifier",)
    ordering_field = "sort_order"
    hide_ordering_field = False

    list_filter = ("section_type", "layout", "is_active", "starts_at", "ends_at")
    search_fields = ("identifier", "title_ne", "title_en")
    readonly_fields = ("id", "homepage_preview", "created_at", "updated_at")
    ordering = ("sort_order", "identifier")
    inlines = (HomeSectionItemInline,)
    actions = ("activate_sections", "deactivate_sections")
    fieldsets = (
        (
            "Identity",
            {
                "fields": (
                    "identifier",
                    "title_ne",
                    "title_en",
                    "subtitle_ne",
                    "subtitle_en",
                    "section_type",
                )
            },
        ),
        (
            "Presentation",
            {
                "fields": ("layout", "max_items"),
                "description": (
                    "Choose a consistent frontend-owned layout. Horizontal rails "
                    "work best for most content; grids suit categories and moods."
                ),
            },
        ),
        (
            "Visibility and scheduling",
            {
                "fields": ("is_active", "starts_at", "ends_at", "sort_order"),
                "description": (
                    "Use start and end times for seasonal sections. End time is "
                    "exclusive, so the section disappears at that exact time."
                ),
            },
        ),
        ("Preview", {"fields": ("homepage_preview",)}),
        (
            "System information",
            {"fields": ("id", "created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_item_count=Count("items"))

    @admin.display(description="Items", ordering="_item_count")
    def item_count(self, obj):
        return obj._item_count

    @display(
        description="Status",
        label={
            "active": "success",
            "upcoming": "warning",
            "expired": "danger",
            "inactive": "info",
        },
    )
    def schedule_badge(self, obj):
        now = timezone.now()
        if obj.ends_at and obj.ends_at <= now:
            return ("expired", "Expired")
        if obj.starts_at and obj.starts_at > now:
            return ("upcoming", "Upcoming")
        if obj.is_active:
            return ("active", "Active")
        return ("inactive", "Inactive")

    @admin.display(description="Homepage preview")
    def homepage_preview(self, obj=None):
        return format_html(
            '<a href="{}" target="_blank" rel="noopener">Preview homepage ↗</a>',
            reverse("home:detail"),
        )

    def get_view_on_site_url(self, obj=None):
        return reverse("home:detail")

    @admin.action(description="Activate selected homepage sections")
    def activate_sections(self, request, queryset):
        updated = home_editorial_service.set_active(
            sections=queryset,
            value=True,
            actor=request.user,
        )
        messages.success(request, f"Activated {updated} homepage section(s).")

    @admin.action(description="Deactivate selected homepage sections")
    def deactivate_sections(self, request, queryset):
        if "confirm_bulk_action" not in request.POST:
            return confirm_bulk_action(
                model_admin=self,
                request=request,
                queryset=queryset,
                action_name="deactivate_sections",
                title="Deactivate homepage sections",
                warning=(
                    "Selected sections will immediately disappear from active "
                    "homepage responses."
                ),
                submit_label="Deactivate sections",
            )
        updated = home_editorial_service.set_active(
            sections=queryset,
            value=False,
            actor=request.user,
        )
        messages.success(request, f"Deactivated {updated} homepage section(s).")

    def get_readonly_fields(self, request, obj=None):
        fields = list(super().get_readonly_fields(request, obj))
        if obj:
            fields.append("section_type")
        return tuple(fields)


@admin.register(HomeSectionItem)
class HomeSectionItemAdmin(ModelAdmin):
    list_display = (
        "section",
        "position",
        "content_target",
        "linked_content_preview",
        "updated_at",
    )
    list_filter = ("section__section_type", "section")
    search_fields = (
        "section__identifier",
        "track__title_ne",
        "playlist__title_ne",
        "album__title_ne",
        "author__name_ne",
        "narrator__name_ne",
        "genre__name_ne",
        "mood__name_ne",
    )
    autocomplete_fields = (
        "section",
        "track",
        "playlist",
        "album",
        "author",
        "narrator",
        "genre",
        "mood",
    )
    readonly_fields = ("id", "created_at", "updated_at")
    list_select_related = (
        "section",
        "track",
        "playlist",
        "album",
        "author",
        "narrator",
        "genre",
        "mood",
    )
    ordering = ("section__sort_order", "position")

    @admin.display(description="Item")
    def content_target(self, obj):
        for field in obj.TARGET_FIELDS:
            value = getattr(obj, field)
            if value is not None:
                return f"{field.title()}: {value}"
        return "—"

    @admin.display(description="Preview")
    def linked_content_preview(self, obj):
        return linked_content_admin_link(obj)


def linked_content_admin_link(item):
    if not item or not item.pk:
        return "Available after saving."
    for field in item.TARGET_FIELDS:
        target = getattr(item, field)
        if target is None:
            continue
        opts = target._meta
        url = reverse(
            f"admin:{opts.app_label}_{opts.model_name}_change",
            args=(target.pk,),
        )
        return format_html(
            '<a href="{}" target="_blank" rel="noopener">{}: {} ↗</a>',
            url,
            field.title(),
            target,
        )
    return "No linked content"
