from datetime import datetime, timedelta

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from apps.common.audit import administrative_audit_service
from apps.common.models import AdministrativeAuditAction
from apps.subscriptions.models import (
    SubscriptionAudit,
    SubscriptionAuditAction,
    SubscriptionStatus,
    UserSubscription,
)


class SubscriptionManagementService:
    """Manual staff transitions; never writes billing-provider-owned fields."""

    snapshot_fields = (
        "status",
        "starts_at",
        "ends_at",
        "trial_ends_at",
        "renewal_at",
        "canceled_at",
        "access_revoked_at",
        "granted_by_id",
    )

    def _authorize(self, actor):
        if not (
            actor
            and actor.is_authenticated
            and actor.is_active
            and actor.is_staff
            and actor.has_perm("subscriptions.change_usersubscription")
        ):
            raise PermissionDenied("Subscription management permission is required.")

    def _reason(self, reason):
        value = (reason or "").strip()
        if not value:
            raise ValidationError("A reason is required for manual changes.")
        return value

    def _duration(self, duration_days):
        try:
            days = int(duration_days)
        except (TypeError, ValueError) as exc:
            raise ValidationError("A valid duration in days is required.") from exc
        if not 1 <= days <= 365:
            raise ValidationError("Duration must be between 1 and 365 days.")
        return timedelta(days=days)

    def _snapshot(self, subscription):
        state = {}
        for field in self.snapshot_fields:
            value = getattr(subscription, field)
            state[field] = value.isoformat() if hasattr(value, "isoformat") else value
            if field == "granted_by_id" and value is not None:
                state[field] = str(value)
        return state

    def _audit(self, *, subscription, actor, action, reason, before):
        audit = SubscriptionAudit.objects.create(
            subscription=subscription,
            actor=actor,
            action=action,
            reason=reason,
            before_state=before,
            after_state=self._snapshot(subscription),
        )
        administrative_audit_service.record(
            actor=actor,
            action=AdministrativeAuditAction.SUBSCRIPTION_CHANGED,
            obj=subscription,
            reason=f"{audit.get_action_display()}: {reason}",
            before=before,
            after=audit.after_state,
        )

    @transaction.atomic
    def grant_temporary(self, *, subscription, actor, reason, duration_days):
        self._authorize(actor)
        reason = self._reason(reason)
        duration = self._duration(duration_days)
        item = UserSubscription.objects.select_for_update().get(pk=subscription.pk)
        before = self._snapshot(item)
        now = timezone.now()
        conflicting = (
            UserSubscription.objects.select_for_update()
            .filter(
                user=item.user,
                status__in=(
                    SubscriptionStatus.ACTIVE,
                    SubscriptionStatus.TRIAL,
                    SubscriptionStatus.STAFF_GRANTED,
                ),
            )
            .exclude(pk=item.pk)
        )
        if conflicting.exists():
            raise ValidationError("The user already has another current subscription.")
        item.status = SubscriptionStatus.STAFF_GRANTED
        item.starts_at = now
        item.ends_at = now + duration
        item.trial_ends_at = None
        item.canceled_at = None
        item.access_revoked_at = None
        item.granted_by = actor
        item.save(
            update_fields=(
                "status",
                "starts_at",
                "ends_at",
                "trial_ends_at",
                "canceled_at",
                "access_revoked_at",
                "granted_by",
                "updated_at",
            )
        )
        self._audit(
            subscription=item,
            actor=actor,
            action=SubscriptionAuditAction.TEMPORARY_ACCESS_GRANTED,
            reason=reason,
            before=before,
        )
        return item

    @transaction.atomic
    def extend(self, *, subscription, actor, reason, duration_days):
        self._authorize(actor)
        reason = self._reason(reason)
        duration = self._duration(duration_days)
        item = UserSubscription.objects.select_for_update().get(pk=subscription.pk)
        before = self._snapshot(item)
        base = max(item.ends_at or timezone.now(), timezone.now())
        item.ends_at = base + duration
        item.save(update_fields=("ends_at", "updated_at"))
        self._audit(
            subscription=item,
            actor=actor,
            action=SubscriptionAuditAction.EXTENDED,
            reason=reason,
            before=before,
        )
        return item

    @transaction.atomic
    def cancel(self, *, subscription, actor, reason):
        self._authorize(actor)
        reason = self._reason(reason)
        item = UserSubscription.objects.select_for_update().get(pk=subscription.pk)
        before = self._snapshot(item)
        item.canceled_at = timezone.now()
        item.save(update_fields=("canceled_at", "updated_at"))
        self._audit(
            subscription=item,
            actor=actor,
            action=SubscriptionAuditAction.CANCELED,
            reason=reason,
            before=before,
        )
        return item

    @transaction.atomic
    def revoke(self, *, subscription, actor, reason):
        self._authorize(actor)
        reason = self._reason(reason)
        item = UserSubscription.objects.select_for_update().get(pk=subscription.pk)
        if item.status == SubscriptionStatus.CANCELED and item.access_revoked_at:
            raise ValidationError("Access is already revoked.")
        before = self._snapshot(item)
        now = timezone.now()
        item.status = SubscriptionStatus.CANCELED
        item.canceled_at = item.canceled_at or now
        item.access_revoked_at = now
        if item.starts_at < now:
            item.ends_at = now
        item.save(
            update_fields=(
                "status",
                "canceled_at",
                "access_revoked_at",
                "ends_at",
                "updated_at",
            )
        )
        self._audit(
            subscription=item,
            actor=actor,
            action=SubscriptionAuditAction.ACCESS_REVOKED,
            reason=reason,
            before=before,
        )
        return item

    @transaction.atomic
    def restore(self, *, subscription, actor, reason):
        self._authorize(actor)
        reason = self._reason(reason)
        item = UserSubscription.objects.select_for_update().get(pk=subscription.pk)
        if not item.access_revoked_at:
            raise ValidationError("Only manually revoked access can be restored.")
        revocation = (
            item.audit_events.filter(action=SubscriptionAuditAction.ACCESS_REVOKED)
            .order_by("-created_at")
            .first()
        )
        if not revocation:
            raise ValidationError("The revocation audit record is missing.")
        previous = revocation.before_state
        previous_status = previous.get("status")
        if previous_status not in {
            SubscriptionStatus.ACTIVE,
            SubscriptionStatus.TRIAL,
            SubscriptionStatus.STAFF_GRANTED,
        }:
            raise ValidationError("The previous subscription state cannot be restored.")
        conflicting = (
            UserSubscription.objects.select_for_update()
            .filter(
                user=item.user,
                status__in=(
                    SubscriptionStatus.ACTIVE,
                    SubscriptionStatus.TRIAL,
                    SubscriptionStatus.STAFF_GRANTED,
                ),
            )
            .exclude(pk=item.pk)
        )
        if conflicting.exists():
            raise ValidationError("The user already has another current subscription.")
        previous_end = previous.get("ends_at")
        if previous_end:
            previous_end = datetime.fromisoformat(previous_end)
            if timezone.is_naive(previous_end):
                previous_end = timezone.make_aware(previous_end)
            if previous_end <= timezone.now():
                raise ValidationError(
                    "Expired access cannot be restored; extend it first."
                )
        before = self._snapshot(item)
        item.status = previous_status
        item.ends_at = previous_end
        item.canceled_at = (
            datetime.fromisoformat(previous["canceled_at"])
            if previous.get("canceled_at")
            else None
        )
        item.access_revoked_at = None
        item.save(
            update_fields=(
                "status",
                "ends_at",
                "canceled_at",
                "access_revoked_at",
                "updated_at",
            )
        )
        self._audit(
            subscription=item,
            actor=actor,
            action=SubscriptionAuditAction.ACCESS_RESTORED,
            reason=reason,
            before=before,
        )
        return item


subscription_management_service = SubscriptionManagementService()
