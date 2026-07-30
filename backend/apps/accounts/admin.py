from urllib.parse import urlencode

from django.contrib import admin, messages
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import models
from django.db.models import Exists, OuterRef
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from unfold.admin import ModelAdmin
from unfold.contrib.filters.admin import (
    BooleanRadioFilter,
    ChoicesDropdownFilter,
    RangeDateTimeFilter,
)
from unfold.decorators import display
from unfold.forms import (
    AdminPasswordChangeForm,
    UserChangeForm,
    UserCreationForm,
)

from apps.accounts.models import SocialIdentity, User
from apps.accounts.services import account_status_service
from apps.common.admin import ImagePreviewAdminMixin, ProtectedDeleteAdminMixin
from apps.common.admin_actions import confirm_bulk_action
from apps.common.admin_performance import (
    is_admin_autocomplete_request,
    is_admin_changelist_request,
)
from apps.subscriptions.models import (
    SubscriptionStatus,
    UserSubscription,
)


@admin.register(SocialIdentity)
class SocialIdentityAdmin(ModelAdmin):
    list_display = ("user", "provider", "email_at_link", "created_at")
    list_filter = ("provider", "created_at")
    search_fields = ("user__email", "email_at_link")
    list_select_related = ("user",)
    readonly_fields = (
        "id",
        "user",
        "provider",
        "subject",
        "email_at_link",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


class PremiumSubscriptionFilter(admin.SimpleListFilter):
    title = "premium subscription"
    parameter_name = "premium"

    def lookups(self, request, model_admin):
        return (("yes", "Premium"), ("no", "Not premium"))

    def queryset(self, request, queryset):
        if self.value() == "yes":
            return queryset.filter(has_premium_subscription=True)
        if self.value() == "no":
            return queryset.filter(has_premium_subscription=False)
        return queryset


class SunneKathaUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "display_name")


class SunneKathaUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User
        fields = "__all__"


@admin.register(User)
class SunneKathaUserAdmin(
    ProtectedDeleteAdminMixin,
    ImagePreviewAdminMixin,
    BaseUserAdmin,
    ModelAdmin,
):
    form = SunneKathaUserChangeForm
    add_form = SunneKathaUserCreationForm
    change_password_form = AdminPasswordChangeForm
    image_field_name = "avatar"
    model = User
    ordering = ("email",)
    list_display = (
        "email",
        "display_name",
        "account_type",
        "staff_status",
        "creator_status",
        "premium_status",
        "active_status",
        "date_joined",
        "last_login",
    )
    list_filter = (
        ("is_active", BooleanRadioFilter),
        ("is_staff", BooleanRadioFilter),
        ("is_superuser", BooleanRadioFilter),
        ("is_creator", BooleanRadioFilter),
        PremiumSubscriptionFilter,
        ("preferred_language", ChoicesDropdownFilter),
        ("date_joined", RangeDateTimeFilter),
    )
    search_fields = ("email", "username", "display_name")
    list_select_related = ()
    actions = ("suspend_accounts", "reactivate_accounts")
    fieldsets = (
        (
            "Identity",
            {
                "fields": (
                    "email",
                    "username",
                    "display_name",
                    "avatar",
                    "image_preview",
                    "first_name",
                    "last_name",
                )
            },
        ),
        (
            "Account Status",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "is_creator",
                    "account_type",
                )
            },
        ),
        (
            "User Preferences",
            {
                "fields": (
                    "preferred_language",
                    "default_playback_speed",
                    "autoplay_enabled",
                    "explicit_content_enabled",
                )
            },
        ),
        (
            "Roles and Permissions",
            {
                "fields": (
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (
            "Subscription",
            {
                "fields": (
                    "premium_status",
                    "subscription_link",
                )
            },
        ),
        (
            "Activity Summary",
            {
                "fields": (
                    "listening_summary_link",
                    "creator_profile_link",
                )
            },
        ),
        (
            "Security Metadata",
            {
                "fields": (
                    "password_management",
                    "id",
                    "last_login",
                    "date_joined",
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )
    readonly_fields = (
        "id",
        "image_preview",
        "last_login",
        "date_joined",
        "created_at",
        "updated_at",
        "account_type",
        "premium_status",
        "subscription_link",
        "listening_summary_link",
        "creator_profile_link",
        "password_management",
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        (
            "SunneKatha profile",
            {
                "fields": (
                    "email",
                    "display_name",
                    "preferred_language",
                    "is_creator",
                )
            },
        ),
    )

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if is_admin_autocomplete_request(request):
            return queryset.only("id", "email", "username", "display_name", "is_active")
        now = timezone.now()
        premium = (
            UserSubscription.objects.filter(
                user_id=OuterRef("pk"),
                status__in=(
                    SubscriptionStatus.ACTIVE,
                    SubscriptionStatus.TRIAL,
                    SubscriptionStatus.STAFF_GRANTED,
                ),
                starts_at__lte=now,
                plan__is_active=True,
            )
            .filter(
                models.Q(status=SubscriptionStatus.STAFF_GRANTED)
                | models.Q(plan__allows_premium_streaming=True),
            )
            .filter(models.Q(ends_at__isnull=True) | models.Q(ends_at__gt=now))
        )
        return (
            queryset.annotate(has_premium_subscription=Exists(premium)).defer(
                "password"
            )
            if is_admin_changelist_request(request)
            else queryset.annotate(has_premium_subscription=Exists(premium))
        )

    def has_change_permission(self, request, obj=None):
        if obj and obj.is_superuser and not request.user.is_superuser:
            return False
        return super().has_change_permission(request, obj)

    def get_readonly_fields(self, request, obj=None):
        fields = list(super().get_readonly_fields(request, obj))
        if not request.user.is_superuser:
            fields.extend(
                (
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            )
        return tuple(dict.fromkeys(fields))

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser:
            if obj.is_superuser:
                raise PermissionDenied("Only a superuser can grant superuser status.")
            if change:
                persisted = User.objects.only(
                    "is_staff",
                    "is_superuser",
                ).get(pk=obj.pk)
                if (
                    obj.is_staff != persisted.is_staff
                    or obj.is_superuser != persisted.is_superuser
                ):
                    raise PermissionDenied(
                        "Only a superuser can change administrative access."
                    )
        super().save_model(request, obj, form, change)

    def save_related(self, request, form, formsets, change):
        if not request.user.is_superuser and change:
            target = form.instance
            persisted = User.objects.get(pk=target.pk)
            submitted_groups = set(
                form.cleaned_data.get("groups", persisted.groups.all()).values_list(
                    "pk",
                    flat=True,
                )
            )
            submitted_permissions = set(
                form.cleaned_data.get(
                    "user_permissions",
                    persisted.user_permissions.all(),
                ).values_list("pk", flat=True)
            )
            if submitted_groups != set(
                persisted.groups.values_list("pk", flat=True)
            ) or submitted_permissions != set(
                persisted.user_permissions.values_list("pk", flat=True)
            ):
                raise PermissionDenied(
                    "Only a superuser can change staff roles or permissions."
                )
        super().save_related(request, form, formsets, change)

    @display(
        description="Account type",
        label={
            "superuser": "danger",
            "staff": "warning",
            "creator": "info",
            "listener": "success",
        },
    )
    def account_type(self, obj):
        if obj.is_superuser:
            return "superuser"
        if obj.is_staff:
            return "staff"
        if obj.is_creator:
            return "creator"
        return "listener"

    @admin.display(description="Staff", boolean=True, ordering="is_staff")
    def staff_status(self, obj):
        return obj.is_staff

    @admin.display(description="Creator", boolean=True, ordering="is_creator")
    def creator_status(self, obj):
        return obj.is_creator

    @display(
        description="Premium",
        ordering="has_premium_subscription",
        label={"premium": "warning", "standard": "info"},
    )
    def premium_status(self, obj):
        return (
            "premium" if getattr(obj, "has_premium_subscription", False) else "standard"
        )

    @admin.display(description="Active", boolean=True, ordering="is_active")
    def active_status(self, obj):
        return obj.is_active

    def _filtered_admin_link(self, *, name, user, label):
        url = reverse(name)
        query = urlencode({"user__id__exact": user.pk})
        return format_html('<a href="{}?{}">{}</a>', url, query, label)

    @admin.display(description="Subscriptions")
    def subscription_link(self, obj):
        return self._filtered_admin_link(
            name="admin:subscriptions_usersubscription_changelist",
            user=obj,
            label="View subscriptions ↗",
        )

    @admin.display(description="Listening activity")
    def listening_summary_link(self, obj):
        progress = self._filtered_admin_link(
            name="admin:library_listeningprogress_changelist",
            user=obj,
            label="Listening progress",
        )
        history = self._filtered_admin_link(
            name="admin:library_listeninghistory_changelist",
            user=obj,
            label="Playback history",
        )
        return format_html("{} · {}", progress, history)

    @admin.display(description="Creator profile")
    def creator_profile_link(self, obj):
        if not hasattr(obj, "creator_profile"):
            return "No creator profile"
        url = reverse(
            "admin:creators_creatorprofile_change",
            args=(obj.creator_profile.pk,),
        )
        return format_html('<a href="{}">Open creator profile ↗</a>', url)

    @admin.display(description="Password")
    def password_management(self, obj):
        if not obj.pk:
            return "Set securely when the account is created."
        url = reverse("admin:auth_user_password_change", args=(obj.pk,))
        return format_html(
            '<a href="{}">Change password securely ↗</a>. '
            "Password hashes and authentication tokens are not displayed.",
            url,
        )

    def _change_account_status(self, request, queryset, *, is_active):
        changed = 0
        skipped = []
        operation = (
            account_status_service.reactivate
            if is_active
            else account_status_service.suspend
        )
        for user in queryset:
            try:
                operation(actor=request.user, user=user)
            except (PermissionDenied, ValidationError) as exc:
                skipped.append(f"{user.email}: {exc}")
            else:
                changed += 1
        if changed:
            self.message_user(
                request,
                f"Updated {changed} account(s).",
                messages.SUCCESS,
            )
        if skipped:
            self.message_user(request, " ".join(skipped), messages.WARNING)

    @admin.action(description="Suspend selected accounts")
    def suspend_accounts(self, request, queryset):
        if "confirm_bulk_action" not in request.POST:
            return confirm_bulk_action(
                model_admin=self,
                request=request,
                queryset=queryset,
                action_name="suspend_accounts",
                title="Suspend selected accounts",
                warning=(
                    "Suspended users are signed out and cannot authenticate until "
                    "an authorized staff member restores access."
                ),
                submit_label="Suspend accounts",
            )
        self._change_account_status(request, queryset, is_active=False)

    @admin.action(description="Reactivate selected accounts")
    def reactivate_accounts(self, request, queryset):
        self._change_account_status(request, queryset, is_active=True)


admin.site.unregister(Group)


@admin.register(Group)
class GroupAdmin(BaseGroupAdmin, ModelAdmin):
    """Keep role composition behind the superuser trust boundary."""

    def has_add_permission(self, request):
        return request.user.is_active and request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_active and request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_active and request.user.is_superuser
