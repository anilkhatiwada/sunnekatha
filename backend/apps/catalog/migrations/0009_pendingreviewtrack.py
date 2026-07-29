from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("catalog", "0008_sync_published_review_status")]

    operations = [
        migrations.CreateModel(
            name="PendingReviewTrack",
            fields=[],
            options={
                "verbose_name": "Pending review",
                "verbose_name_plural": "Pending reviews",
                "proxy": True,
                "indexes": [],
                "constraints": [],
            },
            bases=("catalog.audiotrack",),
        )
    ]
