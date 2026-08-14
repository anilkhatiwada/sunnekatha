from django.db import migrations, models

import apps.common.storage
import apps.common.uploads
import apps.common.validators


class Migration(migrations.Migration):
    dependencies = [("catalog", "0015_replace_content_type_with_category")]

    operations = [
        migrations.AddField(
            model_name="audiotrack",
            name="introduction_audio_file",
            field=models.FileField(
                blank=True,
                help_text=(
                    "Optional prepared spoken introduction. It is used for playlist, "
                    "queue, play-all, and automatic playback, but not direct "
                    "track playback."
                ),
                storage=apps.common.storage.processed_audio_storage,
                upload_to=apps.common.uploads.processed_audio_upload_path,
                validators=[apps.common.validators.validate_audio_upload],
            ),
        ),
        migrations.AddField(
            model_name="audiotrack",
            name="introduction_duration_seconds",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="audiotrack",
            name="introduction_enabled",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="audiotrack",
            name="introduction_notes",
            field=models.TextField(
                blank=True,
                help_text="Internal editorial notes; never returned by the public API.",
            ),
        ),
    ]
