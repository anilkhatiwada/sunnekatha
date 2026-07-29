from django.db import migrations


def mark_published_tracks(apps, schema_editor):
    del schema_editor
    AudioTrack = apps.get_model("catalog", "AudioTrack")
    AudioTrack.objects.filter(is_published=True).update(review_status="published")


def restore_approved_tracks(apps, schema_editor):
    del schema_editor
    AudioTrack = apps.get_model("catalog", "AudioTrack")
    AudioTrack.objects.filter(
        is_published=True,
        review_status="published",
    ).update(review_status="approved")


class Migration(migrations.Migration):
    dependencies = [("catalog", "0007_editorial_review_workflow")]

    operations = [
        migrations.RunPython(
            mark_published_tracks,
            reverse_code=restore_approved_tracks,
        )
    ]
