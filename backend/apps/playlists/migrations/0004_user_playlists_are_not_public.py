from django.db import migrations, models


def make_user_playlists_private(apps, schema_editor):
    del schema_editor
    playlist = apps.get_model("playlists", "Playlist")
    playlist.objects.filter(
        playlist_type="user",
        visibility="public",
    ).update(visibility="private")


class Migration(migrations.Migration):
    dependencies = [("playlists", "0003_playlistitem_position_index")]

    operations = [
        migrations.RunPython(
            make_user_playlists_private,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.AddConstraint(
            model_name="playlist",
            constraint=models.CheckConstraint(
                condition=(
                    ~models.Q(playlist_type="user")
                    | ~models.Q(visibility="public")
                ),
                name="playlist_user_not_public",
            ),
        ),
    ]
