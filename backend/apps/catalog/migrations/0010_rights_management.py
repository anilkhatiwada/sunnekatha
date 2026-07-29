import django.core.validators
import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models

import apps.common.storage
import apps.common.uploads


def replace_unknown_status(apps, schema_editor):
    del schema_editor
    LiteraryWork = apps.get_model("catalog", "LiteraryWork")
    LiteraryWork.objects.filter(copyright_status="unknown").update(
        copyright_status="ownership_unclear"
    )


def restore_unknown_status(apps, schema_editor):
    del schema_editor
    LiteraryWork = apps.get_model("catalog", "LiteraryWork")
    LiteraryWork.objects.filter(copyright_status="ownership_unclear").update(
        copyright_status="unknown"
    )


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("catalog", "0009_pendingreviewtrack"),
    ]

    operations = [
        migrations.AlterField(
            model_name="literarywork",
            name="copyright_status",
            field=models.CharField(
                choices=[
                    ("copyrighted", "Copyrighted"),
                    ("licensed", "Licensed"),
                    ("permission_granted", "Permission granted"),
                    ("public_domain", "Public domain"),
                    ("permission_pending", "Permission pending"),
                    ("permission_expired", "Permission expired"),
                    ("permission_rejected", "Permission rejected"),
                    ("ownership_unclear", "Ownership unclear"),
                    ("unknown", "Unknown (legacy)"),
                ],
                default="unknown",
                max_length=24,
            ),
        ),
        migrations.RunPython(
            replace_unknown_status,
            reverse_code=restore_unknown_status,
        ),
        migrations.CreateModel(
            name="RightsHolder",
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
                ("name", models.CharField(max_length=250)),
                ("contact_email", models.EmailField(blank=True, max_length=254)),
                ("country", models.CharField(blank=True, max_length=120)),
                ("notes", models.TextField(blank=True)),
                ("is_verified", models.BooleanField(db_index=True, default=False)),
            ],
            options={"ordering": ("name", "id")},
        ),
        migrations.CreateModel(
            name="CopyrightLicense",
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
                    "permission_type",
                    models.CharField(
                        choices=[
                            ("audio", "Audio adaptation"),
                            ("commercial", "Commercial use"),
                            ("audio_commercial", "Audio and commercial use"),
                            ("distribution", "Distribution"),
                            ("other", "Other"),
                        ],
                        max_length=24,
                    ),
                ),
                (
                    "effective_date",
                    models.DateField(blank=True, db_index=True, null=True),
                ),
                (
                    "expiration_date",
                    models.DateField(blank=True, db_index=True, null=True),
                ),
                ("territory", models.CharField(blank=True, max_length=250)),
                ("allows_monetization", models.BooleanField(default=False)),
                ("allows_audio", models.BooleanField(default=False)),
                (
                    "verification_status",
                    models.CharField(
                        choices=[
                            ("unverified", "Unverified"),
                            ("pending", "Pending verification"),
                            ("verified", "Verified"),
                            ("rejected", "Verification rejected"),
                        ],
                        db_index=True,
                        default="unverified",
                        max_length=16,
                    ),
                ),
                ("internal_notes", models.TextField(blank=True)),
                (
                    "literary_work",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="copyright_licenses",
                        to="catalog.literarywork",
                    ),
                ),
                (
                    "rights_holder",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="licenses",
                        to="catalog.rightsholder",
                    ),
                ),
            ],
            options={
                "ordering": ("expiration_date", "literary_work__title_ne", "id")
            },
        ),
        migrations.CreateModel(
            name="PermissionDocument",
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
                ("title", models.CharField(max_length=250)),
                (
                    "document",
                    models.FileField(
                        storage=apps.common.storage.original_audio_storage,
                        upload_to=apps.common.uploads.permission_document_upload_path,
                        validators=[
                            django.core.validators.FileExtensionValidator(
                                allowed_extensions=("pdf", "jpg", "jpeg", "png")
                            )
                        ],
                    ),
                ),
                ("is_verified", models.BooleanField(db_index=True, default=False)),
                ("verified_at", models.DateTimeField(blank=True, null=True)),
                (
                    "license",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="documents",
                        to="catalog.copyrightlicense",
                    ),
                ),
                (
                    "verified_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="rights_documents_verified",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ("title", "id")},
        ),
        migrations.AddConstraint(
            model_name="copyrightlicense",
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(("effective_date__isnull", True))
                    | models.Q(("expiration_date__isnull", True))
                    | models.Q(
                        ("expiration_date__gte", models.F("effective_date"))
                    )
                ),
                name="copyright_license_valid_dates",
            ),
        ),
        migrations.AddIndex(
            model_name="copyrightlicense",
            index=models.Index(
                fields=["verification_status", "expiration_date"],
                name="rights_verify_expiry_idx",
            ),
        ),
    ]
