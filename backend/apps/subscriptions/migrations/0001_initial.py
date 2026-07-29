import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("catalog", "0003_alter_audiotrack_storage"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="SubscriptionPlan",
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
                ("slug", models.SlugField(max_length=120, unique=True)),
                ("name", models.CharField(max_length=160)),
                ("description", models.TextField(blank=True)),
                (
                    "access_level",
                    models.CharField(
                        choices=[("free", "Free"), ("premium", "Premium")],
                        default="free",
                        max_length=16,
                    ),
                ),
                ("allows_premium_streaming", models.BooleanField(default=False)),
                ("allows_downloads", models.BooleanField(default=False)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("sort_order", models.PositiveIntegerField(db_index=True, default=0)),
            ],
            options={"ordering": ("sort_order", "name", "id")},
        ),
        migrations.CreateModel(
            name="ContentEntitlement",
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
                ("can_stream", models.BooleanField(default=True)),
                ("can_download", models.BooleanField(default=False)),
                ("starts_at", models.DateTimeField(db_index=True)),
                (
                    "expires_at",
                    models.DateTimeField(blank=True, db_index=True, null=True),
                ),
                ("is_revoked", models.BooleanField(db_index=True, default=False)),
                (
                    "granted_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="content_entitlements_granted",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "track",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="content_entitlements",
                        to="catalog.audiotrack",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="content_entitlements",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ("-starts_at", "id"),
                "constraints": [
                    models.UniqueConstraint(
                        fields=("user", "track"),
                        name="content_entitlement_user_track_unique",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            ("expires_at__isnull", True),
                            ("expires_at__gt", models.F("starts_at")),
                            _connector="OR",
                        ),
                        name="content_entitlement_valid_window",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            ("can_stream", True),
                            ("can_download", True),
                            _connector="OR",
                        ),
                        name="content_entitlement_has_access",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="UserSubscription",
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
                    "status",
                    models.CharField(
                        choices=[
                            ("active", "Active"),
                            ("trial", "Trial"),
                            ("expired", "Expired"),
                            ("canceled", "Canceled"),
                            ("staff_granted", "Staff granted"),
                        ],
                        db_index=True,
                        default="active",
                        max_length=16,
                    ),
                ),
                ("starts_at", models.DateTimeField(db_index=True)),
                (
                    "ends_at",
                    models.DateTimeField(blank=True, db_index=True, null=True),
                ),
                ("canceled_at", models.DateTimeField(blank=True, null=True)),
                (
                    "granted_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="subscriptions_granted",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "plan",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="subscriptions",
                        to="subscriptions.subscriptionplan",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="subscriptions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ("-starts_at", "-created_at", "id"),
                "indexes": [
                    models.Index(
                        fields=["user", "status", "-starts_at"],
                        name="subscription_user_status_idx",
                    )
                ],
                "constraints": [
                    models.CheckConstraint(
                        condition=models.Q(
                            ("ends_at__isnull", True),
                            ("ends_at__gt", models.F("starts_at")),
                            _connector="OR",
                        ),
                        name="subscription_valid_window",
                    ),
                    models.UniqueConstraint(
                        condition=models.Q(
                            (
                                "status__in",
                                ("active", "trial", "staff_granted"),
                            )
                        ),
                        fields=("user",),
                        name="one_current_subscription_per_user",
                    ),
                ],
            },
        ),
    ]
