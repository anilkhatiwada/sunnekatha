import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="AdministrativeAudit",
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
                            ("created", "Content created"),
                            ("edited", "Content edited"),
                            ("review_submitted", "Review submitted"),
                            ("approved", "Approved"),
                            ("rejected", "Rejected"),
                            ("published", "Published"),
                            ("unpublished", "Unpublished"),
                            (
                                "processing_retried",
                                "Audio processing retried",
                            ),
                            ("playlist_reordered", "Playlist reordered"),
                            ("homepage_changed", "Homepage changed"),
                            ("copyright_verified", "Copyright verified"),
                            (
                                "copyright_revoked",
                                "Copyright verification revoked",
                            ),
                            ("subscription_changed", "Subscription changed"),
                            ("user_suspended", "User suspended"),
                            ("user_reactivated", "User reactivated"),
                        ],
                        db_index=True,
                        max_length=32,
                    ),
                ),
                ("object_type", models.CharField(db_index=True, max_length=120)),
                ("object_id", models.CharField(db_index=True, max_length=64)),
                ("object_repr", models.CharField(max_length=250)),
                ("reason", models.TextField(blank=True)),
                ("before_summary", models.JSONField(blank=True, default=dict)),
                ("after_summary", models.JSONField(blank=True, default=dict)),
                (
                    "request_identifier",
                    models.CharField(blank=True, db_index=True, max_length=100),
                ),
                (
                    "staff_user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="administrative_audits",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ("-created_at", "-id"),
                "indexes": [
                    models.Index(
                        fields=["object_type", "object_id", "-created_at"],
                        name="admin_audit_object_idx",
                    ),
                    models.Index(
                        fields=["staff_user", "-created_at"],
                        name="admin_audit_staff_idx",
                    ),
                ],
            },
        )
    ]
