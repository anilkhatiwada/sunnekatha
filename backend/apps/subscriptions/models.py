from django.conf import settings
from django.db import models

from apps.catalog.models import AudioTrack
from apps.common.models import UUIDTimeStampedModel
from apps.common.slugs import generate_unique_slug


class PlanAccessLevel(models.TextChoices):
    FREE = "free", "Free"
    PREMIUM = "premium", "Premium"


class SubscriptionStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    TRIAL = "trial", "Trial"
    EXPIRED = "expired", "Expired"
    CANCELED = "canceled", "Canceled"
    STAFF_GRANTED = "staff_granted", "Staff granted"


class SubscriptionAuditAction(models.TextChoices):
    TEMPORARY_ACCESS_GRANTED = "temporary_access_granted", "Temporary access granted"
    EXTENDED = "extended", "Subscription extended"
    CANCELED = "canceled", "Subscription canceled"
    ACCESS_REVOKED = "access_revoked", "Access revoked"
    ACCESS_RESTORED = "access_restored", "Access restored"


class SubscriptionPlan(UUIDTimeStampedModel):
    slug = models.SlugField(max_length=120, unique=True)
    name = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    access_level = models.CharField(
        max_length=16,
        choices=PlanAccessLevel.choices,
        default=PlanAccessLevel.FREE,
    )
    allows_premium_streaming = models.BooleanField(default=False)
    allows_downloads = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True, db_index=True)
    sort_order = models.PositiveIntegerField(default=0, db_index=True)

    class Meta:
        ordering = ("sort_order", "name", "id")

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(self, self.name, fallback="plan")
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class UserSubscription(UUIDTimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="subscriptions",
        on_delete=models.CASCADE,
    )
    plan = models.ForeignKey(
        SubscriptionPlan,
        related_name="subscriptions",
        on_delete=models.PROTECT,
    )
    status = models.CharField(
        max_length=16,
        choices=SubscriptionStatus.choices,
        default=SubscriptionStatus.ACTIVE,
        db_index=True,
    )
    starts_at = models.DateTimeField(db_index=True)
    ends_at = models.DateTimeField(blank=True, null=True, db_index=True)
    trial_ends_at = models.DateTimeField(blank=True, null=True, db_index=True)
    renewal_at = models.DateTimeField(blank=True, null=True, db_index=True)
    canceled_at = models.DateTimeField(blank=True, null=True)
    access_revoked_at = models.DateTimeField(blank=True, null=True)
    billing_provider = models.CharField(max_length=40, blank=True)
    provider_subscription_id = models.CharField(max_length=255, blank=True)
    provider_data = models.JSONField(default=dict, blank=True)
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="subscriptions_granted",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )

    class Meta:
        ordering = ("-starts_at", "-created_at", "id")
        indexes = [
            models.Index(
                fields=("user", "status", "-starts_at"),
                name="subscription_user_status_idx",
            )
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(ends_at__isnull=True)
                    | models.Q(ends_at__gt=models.F("starts_at"))
                ),
                name="subscription_valid_window",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(trial_ends_at__isnull=True)
                    | models.Q(trial_ends_at__gt=models.F("starts_at"))
                ),
                name="subscription_valid_trial_window",
            ),
            models.UniqueConstraint(
                fields=("user",),
                condition=models.Q(
                    status__in=(
                        SubscriptionStatus.ACTIVE,
                        SubscriptionStatus.TRIAL,
                        SubscriptionStatus.STAFF_GRANTED,
                    )
                ),
                name="one_current_subscription_per_user",
            ),
        ]

    def __str__(self):
        return f"{self.user} — {self.plan}"


class SubscriptionAudit(UUIDTimeStampedModel):
    subscription = models.ForeignKey(
        UserSubscription,
        related_name="audit_events",
        on_delete=models.PROTECT,
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="subscription_manual_changes",
        on_delete=models.PROTECT,
    )
    action = models.CharField(
        max_length=32,
        choices=SubscriptionAuditAction.choices,
        db_index=True,
    )
    reason = models.TextField()
    before_state = models.JSONField(default=dict)
    after_state = models.JSONField(default=dict)

    class Meta:
        ordering = ("-created_at", "-id")
        indexes = [
            models.Index(
                fields=("subscription", "-created_at"),
                name="subscription_audit_event_idx",
            )
        ]

    def __str__(self):
        return f"{self.subscription} — {self.get_action_display()}"


class ContentEntitlement(UUIDTimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="content_entitlements",
        on_delete=models.CASCADE,
    )
    track = models.ForeignKey(
        AudioTrack,
        related_name="content_entitlements",
        on_delete=models.CASCADE,
    )
    can_stream = models.BooleanField(default=True)
    can_download = models.BooleanField(default=False)
    starts_at = models.DateTimeField(db_index=True)
    expires_at = models.DateTimeField(blank=True, null=True, db_index=True)
    is_revoked = models.BooleanField(default=False, db_index=True)
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="content_entitlements_granted",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )

    class Meta:
        ordering = ("-starts_at", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("user", "track"),
                name="content_entitlement_user_track_unique",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(expires_at__isnull=True)
                    | models.Q(expires_at__gt=models.F("starts_at"))
                ),
                name="content_entitlement_valid_window",
            ),
            models.CheckConstraint(
                condition=models.Q(can_stream=True) | models.Q(can_download=True),
                name="content_entitlement_has_access",
            ),
        ]

    def __str__(self):
        return f"{self.user} — {self.track}"
