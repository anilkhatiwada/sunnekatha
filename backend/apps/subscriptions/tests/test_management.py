from datetime import timedelta

import pytest
from django.contrib.admin.helpers import ACTION_CHECKBOX_NAME
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.urls import reverse
from django.utils import timezone

from apps.accounts.tests.factories import UserFactory
from apps.common.models import AdministrativeAudit, AdministrativeAuditAction
from apps.subscriptions.models import (
    SubscriptionAuditAction,
    SubscriptionStatus,
)
from apps.subscriptions.permissions import can_access_premium
from apps.subscriptions.services import subscription_management_service
from apps.subscriptions.tests.factories import UserSubscriptionFactory

pytestmark = pytest.mark.django_db


def subscription_staff():
    user = UserFactory(is_staff=True)
    user.user_permissions.add(
        *Permission.objects.filter(
            content_type__app_label="subscriptions",
            codename__in=("view_usersubscription", "change_usersubscription"),
        )
    )
    return user


def test_temporary_grant_requires_permission_reason_and_records_audit():
    subscription = UserSubscriptionFactory(status=SubscriptionStatus.CANCELED)
    unauthorized = UserFactory(is_staff=True)
    actor = subscription_staff()

    with pytest.raises(PermissionDenied):
        subscription_management_service.grant_temporary(
            subscription=subscription,
            actor=unauthorized,
            reason="Support request",
            duration_days=7,
        )
    with pytest.raises(ValidationError, match="reason"):
        subscription_management_service.grant_temporary(
            subscription=subscription,
            actor=actor,
            reason=" ",
            duration_days=7,
        )

    subscription_management_service.grant_temporary(
        subscription=subscription,
        actor=actor,
        reason="Approved customer recovery",
        duration_days=7,
    )

    subscription.refresh_from_db()
    audit = subscription.audit_events.get()
    assert subscription.status == SubscriptionStatus.STAFF_GRANTED
    assert subscription.granted_by == actor
    assert subscription.ends_at > timezone.now() + timedelta(days=6)
    assert audit.action == SubscriptionAuditAction.TEMPORARY_ACCESS_GRANTED
    assert audit.actor == actor
    assert audit.reason == "Approved customer recovery"
    assert AdministrativeAudit.objects.filter(
        action=AdministrativeAuditAction.SUBSCRIPTION_CHANGED,
        object_id=str(subscription.pk),
        staff_user=actor,
    ).exists()


def test_extend_preserves_billing_provider_data_and_audits_change():
    original_end = timezone.now() + timedelta(days=5)
    provider_data = {"customer": "cus_123", "rawStatus": "active"}
    subscription = UserSubscriptionFactory(
        ends_at=original_end,
        billing_provider="stripe",
        provider_subscription_id="sub_123",
        provider_data=provider_data,
    )

    subscription_management_service.extend(
        subscription=subscription,
        actor=subscription_staff(),
        reason="Service recovery credit",
        duration_days=3,
    )

    subscription.refresh_from_db()
    assert subscription.ends_at == original_end + timedelta(days=3)
    assert subscription.billing_provider == "stripe"
    assert subscription.provider_subscription_id == "sub_123"
    assert subscription.provider_data == provider_data
    assert subscription.audit_events.get().action == SubscriptionAuditAction.EXTENDED


def test_cancel_preserves_access_until_expiration_but_stops_manual_renewal_intent():
    subscription = UserSubscriptionFactory(
        ends_at=timezone.now() + timedelta(days=5),
        renewal_at=timezone.now() + timedelta(days=5),
    )

    subscription_management_service.cancel(
        subscription=subscription,
        actor=subscription_staff(),
        reason="Customer requested cancellation",
    )

    subscription.refresh_from_db()
    assert subscription.canceled_at is not None
    assert subscription.status == SubscriptionStatus.ACTIVE
    assert subscription.renewal_at is not None
    assert can_access_premium(subscription.user)
    assert subscription.audit_events.get().action == SubscriptionAuditAction.CANCELED


def test_revoke_and_restore_access_use_audited_previous_state():
    ends_at = timezone.now() + timedelta(days=5)
    subscription = UserSubscriptionFactory(ends_at=ends_at)
    actor = subscription_staff()

    subscription_management_service.revoke(
        subscription=subscription,
        actor=actor,
        reason="Confirmed account abuse",
    )
    subscription.refresh_from_db()
    assert subscription.status == SubscriptionStatus.CANCELED
    assert subscription.access_revoked_at is not None
    assert not can_access_premium(subscription.user)

    subscription_management_service.restore(
        subscription=subscription,
        actor=actor,
        reason="Investigation cleared the account",
    )
    subscription.refresh_from_db()
    assert subscription.status == SubscriptionStatus.ACTIVE
    assert subscription.access_revoked_at is None
    assert subscription.ends_at == ends_at
    assert can_access_premium(subscription.user)
    assert list(subscription.audit_events.values_list("action", flat=True)) == [
        SubscriptionAuditAction.ACCESS_RESTORED,
        SubscriptionAuditAction.ACCESS_REVOKED,
    ]


def test_admin_action_requires_confirmation_and_reason(client):
    subscription = UserSubscriptionFactory(status=SubscriptionStatus.CANCELED)
    actor = subscription_staff()
    client.force_login(actor)
    url = reverse("admin:subscriptions_usersubscription_changelist")
    action_data = {
        "action": "grant_temporary_premium_access",
        ACTION_CHECKBOX_NAME: str(subscription.pk),
    }

    confirmation = client.post(url, action_data)
    missing_reason = client.post(
        url,
        {
            **action_data,
            "apply": "yes",
            "reason": "",
            "duration_days": "7",
        },
    )
    completed = client.post(
        url,
        {
            **action_data,
            "apply": "yes",
            "reason": "Approved manual grant",
            "duration_days": "7",
        },
    )

    subscription.refresh_from_db()
    assert confirmation.status_code == 200
    assert b"Confirm manual change" in confirmation.content
    assert missing_reason.status_code == 200
    assert b"This field is required" in missing_reason.content
    assert completed.status_code == 302
    assert subscription.status == SubscriptionStatus.STAFF_GRANTED
    assert subscription.audit_events.count() == 1


def test_subscription_admin_displays_lifecycle_columns_and_provider_fields_readonly(
    client,
):
    subscription = UserSubscriptionFactory(
        billing_provider="provider",
        provider_subscription_id="external-id",
        provider_data={"opaque": "preserved"},
    )
    actor = subscription_staff()
    client.force_login(actor)

    changelist = client.get(reverse("admin:subscriptions_usersubscription_changelist"))
    change = client.get(
        reverse(
            "admin:subscriptions_usersubscription_change",
            args=(subscription.pk,),
        )
    )

    assert changelist.status_code == 200
    for heading in (
        "Trial end date",
        "Renewal date",
        "Expiration date",
        "Canceled date",
        "Access status",
        "Created date",
    ):
        assert heading in changelist.content.decode()
    assert change.status_code == 200
    assert b"Billing provider" in change.content
    assert b'name="provider_data"' not in change.content


def test_subscription_admin_disables_unaudited_direct_creation(client):
    actor = subscription_staff()
    actor.user_permissions.add(
        Permission.objects.get(
            content_type__app_label="subscriptions",
            codename="add_usersubscription",
        )
    )
    client.force_login(actor)

    response = client.get(reverse("admin:subscriptions_usersubscription_add"))

    assert response.status_code == 403
