import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("catalog", "0004_track_review_workflow"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="CreatorProfile",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("display_name", models.CharField(max_length=160)),
                ("biography", models.TextField(blank=True)),
                ("roles", models.JSONField(default=list)),
                ("is_approved", models.BooleanField(db_index=True, default=False)),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="creator_profile", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ("-created_at",)},
        ),
        migrations.CreateModel(
            name="RightsLicenseAudit",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("changes", models.JSONField()),
                ("actor", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="rights_license_changes", to=settings.AUTH_USER_MODEL)),
                ("track", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="rights_audits", to="catalog.audiotrack")),
            ],
            options={"ordering": ("-created_at", "id")},
        ),
        migrations.CreateModel(
            name="ContentContributor",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("role", models.CharField(choices=[("narrator", "Narrator"), ("editor", "Editor"), ("content_uploader", "Content uploader"), ("rights_holder", "Rights holder")], max_length=24)),
                ("creator", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="contributions", to="creators.creatorprofile")),
                ("track", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="contributors", to="catalog.audiotrack")),
            ],
            options={"constraints": [models.UniqueConstraint(fields=("track", "creator", "role"), name="creator_track_role_unique")]},
        ),
    ]
