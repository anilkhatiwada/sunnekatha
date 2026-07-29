import factory
from django.utils import timezone
from factory.django import DjangoModelFactory

from apps.accounts.tests.factories import UserFactory
from apps.catalog.tests.factories import AudioTrackFactory
from apps.subscriptions.models import (
    ContentEntitlement,
    PlanAccessLevel,
    SubscriptionPlan,
    SubscriptionStatus,
    UserSubscription,
)


class SubscriptionPlanFactory(DjangoModelFactory):
    class Meta:
        model = SubscriptionPlan

    name = factory.Sequence(lambda number: f"Premium {number}")
    slug = factory.Sequence(lambda number: f"premium-{number}")
    access_level = PlanAccessLevel.PREMIUM
    allows_premium_streaming = True
    allows_downloads = False
    is_active = True


class UserSubscriptionFactory(DjangoModelFactory):
    class Meta:
        model = UserSubscription

    user = factory.SubFactory(UserFactory)
    plan = factory.SubFactory(SubscriptionPlanFactory)
    status = SubscriptionStatus.ACTIVE
    starts_at = factory.LazyFunction(timezone.now)


class ContentEntitlementFactory(DjangoModelFactory):
    class Meta:
        model = ContentEntitlement

    user = factory.SubFactory(UserFactory)
    track = factory.SubFactory(AudioTrackFactory, is_premium=True)
    starts_at = factory.LazyFunction(timezone.now)
    can_stream = True
