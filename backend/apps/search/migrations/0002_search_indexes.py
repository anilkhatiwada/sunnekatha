from django.db import migrations


SEARCH_INDEXES = {
    "search_track_fts_idx": (
        "catalog_audiotrack",
        ("title_ne", "title_en"),
        ("description_ne", "description_en"),
    ),
    "search_work_fts_idx": (
        "catalog_literarywork",
        ("title_ne", "title_en", "subtitle_ne", "subtitle_en"),
        ("description_ne", "description_en"),
    ),
    "search_album_fts_idx": (
        "catalog_album",
        ("title_ne", "title_en"),
        ("description_ne", "description_en"),
    ),
    "search_author_fts_idx": (
        "authors_author",
        ("name_ne", "name_en"),
        ("biography_ne", "biography_en"),
    ),
    "search_narrator_fts_idx": (
        "narrators_narrator",
        ("name_ne", "name_en"),
        ("biography_ne", "biography_en"),
    ),
    "search_playlist_fts_idx": (
        "playlists_playlist",
        ("title_ne", "title_en"),
        ("description_ne", "description_en"),
    ),
    "search_genre_fts_idx": (
        "taxonomy_genre",
        ("name_ne", "name_en"),
        ("description",),
    ),
    "search_mood_fts_idx": (
        "taxonomy_mood",
        ("name_ne", "name_en"),
        ("description",),
    ),
}


def search_vector(fields, weight):
    document = " || ' ' || ".join(
        f"coalesce({field}, '')" for field in fields
    )
    return f"setweight(to_tsvector('simple', {document}), '{weight}')"


def create_search_indexes(apps, schema_editor):
    del apps
    if schema_editor.connection.vendor != "postgresql":
        return
    with schema_editor.connection.cursor() as cursor:
        for name, (table, primary, secondary) in SEARCH_INDEXES.items():
            vector = (
                f"{search_vector(primary, 'A')} || "
                f"{search_vector(secondary, 'B')}"
            )
            cursor.execute(
                f"CREATE INDEX IF NOT EXISTS {name} "
                f"ON {table} USING GIN (({vector}))"
            )
            for field in primary:
                trigram_name = f"{name.removesuffix('_fts_idx')}_{field}_trgm_idx"
                cursor.execute(
                    f"CREATE INDEX IF NOT EXISTS {trigram_name} "
                    f"ON {table} USING GIN ({field} gin_trgm_ops)"
                )


def remove_search_indexes(apps, schema_editor):
    del apps
    if schema_editor.connection.vendor != "postgresql":
        return
    with schema_editor.connection.cursor() as cursor:
        for name, (_, primary, _) in SEARCH_INDEXES.items():
            cursor.execute(f"DROP INDEX IF EXISTS {name}")
            for field in primary:
                trigram_name = f"{name.removesuffix('_fts_idx')}_{field}_trgm_idx"
                cursor.execute(f"DROP INDEX IF EXISTS {trigram_name}")


class Migration(migrations.Migration):
    dependencies = [
        ("authors", "0002_author_author_death_not_before_birth"),
        ("catalog", "0002_audiotrack"),
        ("narrators", "0001_initial"),
        ("playlists", "0002_playlist_playlist_type_owner_valid_and_more"),
        ("search", "0001_initial"),
        ("taxonomy", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(
            create_search_indexes,
            reverse_code=remove_search_indexes,
        )
    ]
