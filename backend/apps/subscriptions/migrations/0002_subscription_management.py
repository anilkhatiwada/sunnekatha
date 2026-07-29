import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("subscriptions", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="usersubscription",
            name="access_revoked_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="usersubscription",
            name="billing_provider",
            field=models.CharField(blank=True, max_length=40),
        ),
        migrations.AddField(
            model_name="usersubscription",
            name="provider_data",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="usersubscription",
            name="provider_subscription_id",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="usersubscription",
            name="renewal_at",
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name="usersubscription",
            name="trial_ends_at",
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
        migrations.AddConstraint(
            model_name="usersubscription",
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(("trial_ends_at__isnull", True))
                    | models.Q(("trial_ends_at__gt", models.F("starts_at")))
                ),
                name="subscription_valid_trial_window",
            ),
        ),
        migrations.CreateModel(
            name="SubscriptionAudit",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "action",
                    models.CharField(
                        choices=[
                            (
                                "temporary_access_granted",
                                "Temporary access granted",
                            ),
                            ("extended", "Subscription extended"),
                            ("canceled", "Subscription canceled"),
                            ("access_revoked", "Access revoked"),
                            ("access_restored", "Access restored"),
                        ],
                        db_index=True,
                        max_length=32,
                    ),
                ),
                ("reason", models.TextField()),
                ("before_state", models.JSONField(default=dict)),
                ("after_state", models.JSONField(default=dict)),
                (
                    "actor",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="subscription_manual_changes",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "subscription",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="audit_events",
                        to="subscriptions.usersubscription",
                    ),
                ),
            ],
            options={
                "ordering": ("-created_at", "-id"),
                "indexes": [
                    models.Index(
                        fields=["subscription", "-created_at"],
                        name="subscription_audit_event_idx",
                    )
                ],
            },
        ),
    ]
