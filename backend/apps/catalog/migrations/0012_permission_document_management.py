import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("catalog", "0011_default_ownership_unclear"),
    ]

    operations = [
        migrations.AddField(
            model_name="permissiondocument",
            name="document_type",
            field=models.CharField(
                choices=[
                    ("license", "License agreement"),
                    ("consent", "Consent letter"),
                    ("ownership", "Ownership evidence"),
                    ("public_domain", "Public-domain evidence"),
                    ("other", "Other"),
                ],
                default="license",
                max_length=24,
            ),
        ),
        migrations.AddField(
            model_name="permissiondocument",
            name="notes",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="permissiondocument",
            name="uploaded_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="rights_documents_uploaded",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.CreateModel(
            name="PermissionDocumentAudit",
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
                            ("verified", "Verified"),
                            ("verification_revoked", "Verification revoked"),
                            ("downloaded", "Downloaded"),
                        ],
                        db_index=True,
                        max_length=24,
                    ),
                ),
                ("details", models.JSONField(blank=True, default=dict)),
                (
                    "actor",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="permission_document_audits",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "document",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="audit_events",
                        to="catalog.permissiondocument",
                    ),
                ),
            ],
            options={"ordering": ("-created_at", "-id")},
        ),
        migrations.AddIndex(
            model_name="permissiondocumentaudit",
            index=models.Index(
                fields=["document", "-created_at"],
                name="permission_doc_audit_idx",
            ),
        ),
    ]
