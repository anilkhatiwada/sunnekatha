from datetime import timedelta

from django import forms
from django.contrib import admin, messages
from django.contrib.admin.helpers import ACTION_CHECKBOX_NAME
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.template.response import TemplateResponse
from django.utils import timezone
from unfold.admin import ModelAdmin, TabularInline
from unfold.contrib.filters.admin import (
    AutocompleteSelectFilter,
    ChoicesDropdownFilter,
    RangeDateTimeFilter,
)
from unfold.decorators import display

from apps.common.admin import ProtectedDeleteAdminMixin
from apps.subscriptions.models import (
    ContentEntitlement,
    SubscriptionAudit,
    SubscriptionPlan,
    SubscriptionStatus,
    UserSubscription,
)
from apps.subscriptions.services import subscription_management_service


class SubscriptionLifecycleFilter(admin.SimpleListFilter):
    title = "access lifecycle"
    parameter_name = "lifecycle"

    def lookups(self, request, model_admin):
        return (
            ("active", "Active"),
            ("trial", "Trial"),
            ("expired", "Expired"),
            ("canceled", "Canceled"),
            ("expiring", "Expiring within 30 days"),
        )

    def queryset(self, request, queryset):
        now = timezone.now()
        current = Q(starts_at__lte=now) & (Q(ends_at__isnull=True) | Q(ends_at__gt=now))
        if self.value() == "active":
            return queryset.filter(
                current,
                status__in=(
                    SubscriptionStatus.ACTIVE,
                    SubscriptionStatus.STAFF_GRANTED,
                ),
                access_revoked_at__isnull=True,
            )
        if self.value() == "trial":
            return queryset.filter(
                current,
                status=SubscriptionStatus.TRIAL,
                access_revoked_at__isnull=True,
            )
        if self.value() == "expired":
            return queryset.filter(
                Q(status=SubscriptionStatus.EXPIRED) | Q(ends_at__lte=now)
            )
        if self.value() == "canceled":
            return queryset.filter(canceled_at__isnull=False)
        if self.value() == "expiring":
            return queryset.filter(
                ends_at__gt=now,
                ends_at__lte=now + timedelta(days=30),
                access_revoked_at__isnull=True,
            )
        return queryset


class SubscriptionActionForm(forms.Form):
    reason = forms.CharField(
        label="Reason",
        widget=forms.Textarea(attrs={"rows": 4}),
        help_text="Required. This is stored in the immutable audit trail.",
    )
    duration_days = forms.IntegerField(
        label="Duration in days",
        min_value=1,
        max_value=365,
        required=False,
    )


class SubscriptionAuditInline(TabularInline):
    model = SubscriptionAudit
    extra = 0
    can_delete = False
    fields = ("action", "actor", "reason", "created_at")
    readonly_fields = fields
    ordering = ("-created_at",)

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(ProtectedDeleteAdminMixin, ModelAdmin):
    list_display = (
        "name",
        "access_level",
        "allows_premium_streaming",
        "allows_downloads",
        "is_active",
        "sort_order",
    )
    list_filter = ("access_level", "is_active", "allows_downloads")
    search_fields = ("name", "slug", "description")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("sort_order", "name")
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(UserSubscription)
class UserSubscriptionAdmin(ProtectedDeleteAdminMixin, ModelAdmin):
    list_display = (
        "user",
        "plan",
        "status",
        "start_date",
        "trial_end_date",
        "renewal_date",
        "expiration_date",
        "canceled_date",
        "access_status",
        "created_date",
    )
    list_filter = (
        ("plan", AutocompleteSelectFilter),
        ("status", ChoicesDropdownFilter),
        SubscriptionLifecycleFilter,
        ("starts_at", RangeDateTimeFilter),
        ("ends_at", RangeDateTimeFilter),
    )
    search_fields = ("user__email", "user__username", "plan__name")
    autocomplete_fields = ("user", "plan", "granted_by")
    readonly_fields = (
        "id",
        "access_status",
        "billing_provider",
        "provider_subscription_id",
        "provider_data",
        "access_revoked_at",
        "created_at",
        "updated_at",
    )
    list_select_related = ("user", "plan", "granted_by")
    date_hierarchy = "starts_at"
    inlines = (SubscriptionAuditInline,)
    actions = (
        "grant_temporary_premium_access",
        "extend_subscription",
        "cancel_subscription",
        "revoke_access",
        "restore_access",
    )
    fieldsets = (
        (
            "Subscription",
            {"fields": ("user", "plan", "status", "access_status")},
        ),
        (
            "Lifecycle",
            {
                "fields": (
                    "starts_at",
                    "trial_ends_at",
                    "renewal_at",
                    "ends_at",
                    "canceled_at",
                    "access_revoked_at",
                )
            },
        ),
        (
            "Manual grant",
            {"fields": ("granted_by",)},
        ),
        (
            "Billing provider — read only",
            {
                "classes": ("collapse",),
                "fields": (
                    "billing_provider",
                    "provider_subscription_id",
                    "provider_data",
                ),
            },
        ),
        (
            "System metadata",
            {
                "classes": ("collapse",),
                "fields": ("id", "created_at", "updated_at"),
            },
        ),
    )

    def has_add_permission(self, request):
        return False

    def get_readonly_fields(self, request, obj=None):
        fields = list(super().get_readonly_fields(request, obj))
        if obj:
            fields.extend(
                (
                    "user",
                    "plan",
                    "status",
                    "starts_at",
                    "trial_ends_at",
                    "renewal_at",
                    "ends_at",
                    "canceled_at",
                    "granted_by",
                )
            )
        return tuple(dict.fromkeys(fields))

    @display(
        description="Access status",
        label={
            "active": "success",
            "trial": "info",
            "scheduled": "info",
            "expiring": "warning",
            "canceled": "warning",
            "revoked": "danger",
            "expired": "danger",
        },
    )
    def access_status(self, obj):
        now = timezone.now()
        if obj.access_revoked_at:
            return "revoked"
        if obj.status == SubscriptionStatus.EXPIRED or (
            obj.ends_at and obj.ends_at <= now
        ):
            return "expired"
        if obj.starts_at > now:
            return "scheduled"
        if obj.canceled_at:
            return "canceled"
        if obj.status == SubscriptionStatus.TRIAL:
            return "trial"
        if obj.ends_at and obj.ends_at <= now + timedelta(days=30):
            return "expiring"
        return "active"

    @admin.display(description="Start date", ordering="starts_at")
    def start_date(self, obj):
        return obj.starts_at

    @admin.display(description="Trial end date", ordering="trial_ends_at")
    def trial_end_date(self, obj):
        return obj.trial_ends_at

    @admin.display(description="Renewal date", ordering="renewal_at")
    def renewal_date(self, obj):
        return obj.renewal_at

    @admin.display(description="Expiration date", ordering="ends_at")
    def expiration_date(self, obj):
        return obj.ends_at

    @admin.display(description="Canceled date", ordering="canceled_at")
    def canceled_date(self, obj):
        return obj.canceled_at

    @admin.display(description="Created date", ordering="created_at")
    def created_date(self, obj):
        return obj.created_at

    def _action_confirmation(
        self,
        request,
        queryset,
        *,
        operation,
        title,
        needs_duration=False,
    ):
        if request.POST.get("apply") == "yes":
            form = SubscriptionActionForm(request.POST)
            is_valid = form.is_valid()
            if is_valid and needs_duration and not form.cleaned_data["duration_days"]:
                form.add_error("duration_days", "A duration is required.")
                is_valid = False
            if is_valid:
                changed = 0
                errors = []
                service_method = getattr(subscription_management_service, operation)
                for subscription in queryset.select_related("user", "plan"):
                    kwargs = {
                        "subscription": subscription,
                        "actor": request.user,
                        "reason": form.cleaned_data["reason"],
                    }
                    if needs_duration:
                        kwargs["duration_days"] = form.cleaned_data["duration_days"]
                    try:
                        service_method(**kwargs)
                    except ValidationError as exc:
                        errors.append(f"{subscription}: {'; '.join(exc.messages)}")
                    else:
                        changed += 1
                if changed:
                    self.message_user(
                        request,
                        f"Updated {changed} subscription(s).",
                        messages.SUCCESS,
                    )
                if errors:
                    self.message_user(request, " ".join(errors), messages.WARNING)
                return None
        else:
            form = SubscriptionActionForm()

        context = {
            **self.admin_site.each_context(request),
            "title": title,
            "opts": self.model._meta,
            "subscriptions": queryset.select_related("user", "plan"),
            "form": form,
            "action_name": request.POST.get("action"),
            "selected_ids": request.POST.getlist(ACTION_CHECKBOX_NAME),
            "action_checkbox_name": ACTION_CHECKBOX_NAME,
            "needs_duration": needs_duration,
        }
        return TemplateResponse(
            request,
            "admin/subscriptions/usersubscription/action_confirmation.html",
            context,
        )

    @admin.action(description="Grant temporary premium access")
    def grant_temporary_premium_access(self, request, queryset):
        return self._action_confirmation(
            request,
            queryset,
            operation="grant_temporary",
            title="Grant temporary premium access",
            needs_duration=True,
        )

    @admin.action(description="Extend subscription")
    def extend_subscription(self, request, queryset):
        return self._action_confirmation(
            request,
            queryset,
            operation="extend",
            title="Extend subscriptions",
            needs_duration=True,
        )

    @admin.action(description="Cancel subscription")
    def cancel_subscription(self, request, queryset):
        return self._action_confirmation(
            request,
            queryset,
            operation="cancel",
            title="Cancel subscriptions at the current expiration",
        )

    @admin.action(description="Revoke access immediately")
    def revoke_access(self, request, queryset):
        return self._action_confirmation(
            request,
            queryset,
            operation="revoke",
            title="Revoke subscription access immediately",
        )

    @admin.action(description="Restore manually revoked access")
    def restore_access(self, request, queryset):
        return self._action_confirmation(
            request,
            queryset,
            operation="restore",
            title="Restore manually revoked access",
        )


@admin.register(SubscriptionAudit)
class SubscriptionAuditAdmin(ModelAdmin):
    list_display = ("subscription", "action", "actor", "reason", "created_at")
    list_filter = ("action", "created_at")
    search_fields = (
        "subscription__user__email",
        "subscription__plan__name",
        "actor__email",
        "reason",
    )
    list_select_related = ("subscription", "subscription__user", "actor")
    readonly_fields = (
        "id",
        "subscription",
        "actor",
        "action",
        "reason",
        "before_state",
        "after_state",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ContentEntitlement)
class ContentEntitlementAdmin(ProtectedDeleteAdminMixin, ModelAdmin):
    list_display = (
        "user",
        "track",
        "can_stream",
        "can_download",
        "starts_at",
        "expires_at",
        "is_revoked",
    )
    list_filter = ("can_stream", "can_download", "is_revoked")
    search_fields = ("user__email", "track__title_ne", "track__title_en")
    autocomplete_fields = ("user", "track", "granted_by")
    readonly_fields = ("id", "created_at", "updated_at")
    list_select_related = ("user", "track", "granted_by")
    date_hierarchy = "starts_at"
