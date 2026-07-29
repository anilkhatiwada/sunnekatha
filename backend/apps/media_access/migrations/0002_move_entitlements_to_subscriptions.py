from django.db import migrations
from django.utils import timezone


def move_entitlements(apps, schema_editor):
    del schema_editor
    PremiumEntitlement = apps.get_model("media_access", "PremiumEntitlement")
    SubscriptionPlan = apps.get_model("subscriptions", "SubscriptionPlan")
    UserSubscription = apps.get_model("subscriptions", "UserSubscription")
    plan, _ = SubscriptionPlan.objects.get_or_create(
        slug="legacy-premium",
        defaults={
            "name": "Legacy Premium",
            "description": "Migrated from the temporary media entitlement.",
            "access_level": "premium",
            "allows_premium_streaming": True,
            "allows_downloads": False,
            "is_active": True,
        },
    )
    now = timezone.now()
    for entitlement in PremiumEntitlement.objects.iterator():
        status = (
            "canceled"
            if entitlement.is_revoked
            else "expired"
            if entitlement.expires_at <= now
            else "active"
        )
        UserSubscription.objects.create(
            user_id=entitlement.user_id,
            plan=plan,
            status=status,
            starts_at=entitlement.starts_at,
            ends_at=entitlement.expires_at,
            canceled_at=now if entitlement.is_revoked else None,
        )


def restore_entitlements(apps, schema_editor):
    del schema_editor
    PremiumEntitlement = apps.get_model("media_access", "PremiumEntitlement")
    UserSubscription = apps.get_model("subscriptions", "UserSubscription")
    for subscription in UserSubscription.objects.filter(
        plan__slug="legacy-premium"
    ).iterator():
        PremiumEntitlement.objects.update_or_create(
            user_id=subscription.user_id,
            defaults={
                "starts_at": subscription.starts_at,
                "expires_at": subscription.ends_at,
                "is_revoked": subscription.status == "canceled",
            },
        )


class Migration(migrations.Migration):
    dependencies = [
        ("media_access", "0001_initial"),
        ("subscriptions", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(move_entitlements, restore_entitlements),
        migrations.DeleteModel(name="PremiumEntitlement"),
    ]
