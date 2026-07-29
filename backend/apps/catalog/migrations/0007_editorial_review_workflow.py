import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("catalog", "0006_audioprocessingjob_retry_audit"),
    ]

    operations = [
        migrations.AlterField(
            model_name="audiotrack",
            name="review_status",
            field=models.CharField(
                choices=[
                    ("draft", "Draft"),
                    ("submitted", "Submitted"),
                    ("changes_requested", "Changes requested"),
                    ("approved", "Approved"),
                    ("scheduled", "Scheduled"),
                    ("published", "Published"),
                    ("rejected", "Rejected"),
                    ("archived", "Archived"),
                ],
                db_index=True,
                default="draft",
                max_length=24,
            ),
        ),
        migrations.AddField(
            model_name="audiotrack",
            name="review_comments",
            field=models.TextField(blank=True),
        ),
        migrations.AlterModelOptions(
            name="audiotrack",
            options={
                "ordering": (
                    "album_id",
                    "track_number",
                    "chapter_number",
                    "title_ne",
                    "id",
                ),
                "permissions": [
                    ("approve_audiotrack", "Can approve audio track submissions"),
                    (
                        "publish_audiotrack",
                        "Can schedule and publish audio tracks",
                    ),
                    (
                        "approve_own_audiotrack",
                        "Can approve own audio track submissions",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="TrackReviewEvent",
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
                    "from_status",
                    models.CharField(
                        choices=[
                            ("draft", "Draft"),
                            ("submitted", "Submitted"),
                            ("changes_requested", "Changes requested"),
                            ("approved", "Approved"),
                            ("scheduled", "Scheduled"),
                            ("published", "Published"),
                            ("rejected", "Rejected"),
                            ("archived", "Archived"),
                        ],
                        max_length=24,
                    ),
                ),
                (
                    "to_status",
                    models.CharField(
                        choices=[
                            ("draft", "Draft"),
                            ("submitted", "Submitted"),
                            ("changes_requested", "Changes requested"),
                            ("approved", "Approved"),
                            ("scheduled", "Scheduled"),
                            ("published", "Published"),
                            ("rejected", "Rejected"),
                            ("archived", "Archived"),
                        ],
                        max_length=24,
                    ),
                ),
                ("comment", models.TextField(blank=True)),
                ("scheduled_for", models.DateTimeField(blank=True, null=True)),
                (
                    "actor",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="track_review_events",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "track",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="review_events",
                        to="catalog.audiotrack",
                    ),
                ),
            ],
            options={"ordering": ("-created_at", "-id")},
        ),
        migrations.AddIndex(
            model_name="trackreviewevent",
            index=models.Index(
                fields=["track", "-created_at"],
                name="track_review_event_track_idx",
            ),
        ),
    ]
