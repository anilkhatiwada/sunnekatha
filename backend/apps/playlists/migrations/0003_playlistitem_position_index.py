from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("playlists", "0002_playlist_playlist_type_owner_valid_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="playlistitem",
            name="position",
            field=models.PositiveIntegerField(db_index=True),
        ),
    ]
