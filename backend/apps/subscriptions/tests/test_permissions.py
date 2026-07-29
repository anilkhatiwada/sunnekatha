from datetime import timedelta

import pytest
from django.utils import timezone

from apps.accounts.tests.factories import UserFactory
from apps.catalog.tests.factories import AudioTrackFactory
from apps.subscriptions.models import SubscriptionStatus
from apps.subscriptions.permissions import (
    can_access_premium,
    can_download_track,
    can_stream_track,
)
from apps.subscriptions.tests.factories import (
    ContentEntitlementFactory,
    SubscriptionPlanFactory,
    UserSubscriptionFactory,
)

pytestmark = pytest.mark.django_db


def test_free_user_can_stream_free_but_not_premium_track():
    user = UserFactory()

    assert can_stream_track(user, AudioTrackFactory(is_premium=False))
    assert not can_stream_track(user, AudioTrackFactory(is_premium=True))
    assert not can_access_premium(user)


@pytest.mark.parametrize(
    "subscription_status",
    [
        SubscriptionStatus.ACTIVE,
        SubscriptionStatus.TRIAL,
        SubscriptionStatus.STAFF_GRANTED,
    ],
)
def test_current_premium_states_allow_premium_streaming(subscription_status):
    subscription = UserSubscriptionFactory(status=subscription_status)

    assert can_access_premium(subscription.user)
    assert can_stream_track(
        subscription.user,
        AudioTrackFactory(is_premium=True),
    )


def test_staff_granted_status_overrides_free_plan_capability():
    free_plan = SubscriptionPlanFactory(
        access_level="free",
        allows_premium_streaming=False,
    )
    subscription = UserSubscriptionFactory(
        plan=free_plan,
        status=SubscriptionStatus.STAFF_GRANTED,
    )

    assert can_access_premium(subscription.user)


@pytest.mark.parametrize(
    "subscription_status",
    [SubscriptionStatus.EXPIRED, SubscriptionStatus.CANCELED],
)
def test_terminal_subscription_states_deny_premium(subscription_status):
    subscription = UserSubscriptionFactory(status=subscription_status)

    assert not can_access_premium(subscription.user)
    assert not can_stream_track(
        subscription.user,
        AudioTrackFactory(is_premium=True),
    )


def test_ended_or_future_subscription_is_not_current():
    now = timezone.now()
    expired = UserSubscriptionFactory(
        starts_at=now - timedelta(days=2),
        ends_at=now - timedelta(seconds=1),
    )
    future = UserSubscriptionFactory(
        starts_at=now + timedelta(days=1),
    )

    assert not can_access_premium(expired.user)
    assert not can_access_premium(future.user)


def test_track_entitlement_can_grant_stream_without_subscription():
    track = AudioTrackFactory(is_premium=True)
    entitlement = ContentEntitlementFactory(track=track)

    assert can_stream_track(entitlement.user, track)
    assert not can_access_premium(entitlement.user)


def test_expired_or_revoked_content_entitlement_is_denied():
    now = timezone.now()
    expired_track = AudioTrackFactory(is_premium=True)
    revoked_track = AudioTrackFactory(is_premium=True)
    expired = ContentEntitlementFactory(
        track=expired_track,
        starts_at=now - timedelta(days=1),
        expires_at=now - timedelta(seconds=1),
    )
    revoked = ContentEntitlementFactory(track=revoked_track, is_revoked=True)

    assert not can_stream_track(expired.user, expired_track)
    assert not can_stream_track(revoked.user, revoked_track)


def test_download_requires_plan_or_content_download_permission():
    track = AudioTrackFactory()
    no_download = UserSubscriptionFactory()
    download_plan = SubscriptionPlanFactory(allows_downloads=True)
    download_subscription = UserSubscriptionFactory(plan=download_plan)
    direct = ContentEntitlementFactory(
        track=track,
        can_stream=False,
        can_download=True,
    )

    assert not can_download_track(no_download.user, track)
    assert can_download_track(download_subscription.user, track)
    assert can_download_track(direct.user, track)
    assert can_download_track(UserFactory(is_staff=True), track)
