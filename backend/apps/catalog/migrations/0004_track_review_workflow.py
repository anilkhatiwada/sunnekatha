import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def mark_existing_published_tracks_approved(apps, schema_editor):
    del schema_editor
    AudioTrack = apps.get_model("catalog", "AudioTrack")
    AudioTrack.objects.filter(is_published=True).update(review_status="approved")


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("catalog", "0003_alter_audiotrack_storage"),
    ]

    operations = [
        migrations.AddField(
            model_name="audiotrack",
            name="review_status",
            field=models.CharField(
                choices=[
                    ("draft", "Draft"),
                    ("submitted", "Submitted"),
                    ("approved", "Approved"),
                    ("rejected", "Rejected"),
                ],
                db_index=True,
                default="draft",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="audiotrack",
            name="reviewed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="audiotrack",
            name="reviewed_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="tracks_reviewed",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="audiotrack",
            name="submitted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RunPython(
            mark_existing_published_tracks_approved,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
