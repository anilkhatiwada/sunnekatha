from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("notifications", "0001_initial")]

    operations = [
        migrations.AlterField(
            model_name="notification",
            name="notification_type",
            field=models.CharField(
                choices=[
                    (
                        "followed_author_published",
                        "Followed author published new content",
                    ),
                    (
                        "followed_narrator_published",
                        "Followed narrator published new content",
                    ),
                    ("playlist_updated", "Playlist updated"),
                    (
                        "upload_processing_completed",
                        "Upload processing completed",
                    ),
                    ("upload_processing_failed", "Upload processing failed"),
                    (
                        "creator_submission_approved",
                        "Creator submission approved",
                    ),
                    (
                        "creator_submission_rejected",
                        "Creator submission rejected",
                    ),
                    (
                        "creator_changes_requested",
                        "Creator submission changes requested",
                    ),
                ],
                db_index=True,
                max_length=48,
            ),
        )
    ]
