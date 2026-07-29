import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]

    operations = [
        migrations.CreateModel(
            name="PremiumEntitlement",
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
                ("starts_at", models.DateTimeField()),
                ("expires_at", models.DateTimeField(db_index=True)),
                ("is_revoked", models.BooleanField(db_index=True, default=False)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="premium_entitlement",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ("-expires_at",),
                "constraints": [
                    models.CheckConstraint(
                        condition=models.Q(
                            ("expires_at__gt", models.F("starts_at"))
                        ),
                        name="premium_entitlement_valid_window",
                    )
                ],
            },
        )
    ]
