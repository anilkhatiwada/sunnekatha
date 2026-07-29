from django.db.models import Q
from django.utils import timezone

from apps.subscriptions.models import (
    ContentEntitlement,
    SubscriptionStatus,
    UserSubscription,
)

CURRENT_STATUSES = (
    SubscriptionStatus.ACTIVE,
    SubscriptionStatus.TRIAL,
    SubscriptionStatus.STAFF_GRANTED,
)


def _is_active_user(user):
    return bool(user and user.is_authenticated and user.is_active)


def current_subscription(user, *, at=None):
    if not _is_active_user(user):
        return None
    moment = at or timezone.now()
    return (
        UserSubscription.objects.filter(
            user=user,
            status__in=CURRENT_STATUSES,
            starts_at__lte=moment,
            plan__is_active=True,
        )
        .filter(Q(ends_at__isnull=True) | Q(ends_at__gt=moment))
        .select_related("plan")
        .first()
    )


def can_access_premium(user, *, at=None):
    if _is_active_user(user) and user.is_staff:
        return True
    subscription = current_subscription(user, at=at)
    return bool(
        subscription
        and (
            subscription.status == SubscriptionStatus.STAFF_GRANTED
            or subscription.plan.allows_premium_streaming
        )
    )


def active_content_entitlement(user, track, *, permission, at=None):
    if not _is_active_user(user):
        return False
    moment = at or timezone.now()
    return (
        ContentEntitlement.objects.filter(
            user=user,
            track=track,
            starts_at__lte=moment,
            is_revoked=False,
            **{permission: True},
        )
        .filter(Q(expires_at__isnull=True) | Q(expires_at__gt=moment))
        .exists()
    )


def can_stream_track(user, track, *, at=None):
    if not track.is_premium:
        return True
    return premium_access_type(user, track=track, at=at) is not None


def premium_access_type(user, *, track=None, at=None):
    if _is_active_user(user) and user.is_staff:
        return "staff"
    subscription = current_subscription(user, at=at)
    if subscription and (
        subscription.status == SubscriptionStatus.STAFF_GRANTED
        or subscription.plan.allows_premium_streaming
    ):
        return subscription.status
    if track and active_content_entitlement(
        user,
        track,
        permission="can_stream",
        at=at,
    ):
        return "content_entitlement"
    return None


def can_download_track(user, track, *, at=None):
    if _is_active_user(user) and user.is_staff:
        return True
    if active_content_entitlement(
        user,
        track,
        permission="can_download",
        at=at,
    ):
        return True
    subscription = current_subscription(user, at=at)
    return bool(subscription and subscription.plan.allows_downloads)
