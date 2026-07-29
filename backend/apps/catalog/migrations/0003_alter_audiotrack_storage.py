from django.db import migrations, models

import apps.common.storage
import apps.common.uploads
import apps.common.validators


class Migration(migrations.Migration):
    dependencies = [("catalog", "0002_audiotrack")]

    operations = [
        migrations.AlterField(
            model_name="audiotrack",
            name="audio_master_file",
            field=models.FileField(
                blank=True,
                storage=apps.common.storage.original_audio_storage,
                upload_to=apps.common.uploads.original_audio_upload_path,
                validators=[apps.common.validators.validate_audio_upload],
            ),
        ),
        migrations.AlterField(
            model_name="audiotrack",
            name="stream_file_high",
            field=models.FileField(
                blank=True,
                storage=apps.common.storage.processed_audio_storage,
                upload_to=apps.common.uploads.processed_audio_upload_path,
                validators=[apps.common.validators.validate_audio_upload],
            ),
        ),
        migrations.AlterField(
            model_name="audiotrack",
            name="stream_file_low",
            field=models.FileField(
                blank=True,
                storage=apps.common.storage.processed_audio_storage,
                upload_to=apps.common.uploads.processed_audio_upload_path,
                validators=[apps.common.validators.validate_audio_upload],
            ),
        ),
    ]
