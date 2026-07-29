import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("catalog", "0005_audioprocessingjob"),
    ]

    operations = [
        migrations.AddField(
            model_name="audioprocessingjob",
            name="retry_initiated_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="initiated_audio_processing_retries",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="audioprocessingjob",
            name="retry_requested_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
