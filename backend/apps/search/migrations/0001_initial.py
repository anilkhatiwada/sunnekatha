import uuid

import django.contrib.postgres.indexes
import django.contrib.postgres.operations
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        django.contrib.postgres.operations.TrigramExtension(),
        django.contrib.postgres.operations.UnaccentExtension(),
        migrations.CreateModel(
            name="SearchAlias",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "entity_type",
                    models.CharField(
                        choices=[
                            ("track", "Track"),
                            ("literary_work", "Literary work"),
                            ("author", "Author"),
                            ("narrator", "Narrator"),
                            ("playlist", "Playlist"),
                            ("album", "Album"),
                            ("genre", "Genre"),
                            ("mood", "Mood"),
                        ],
                        max_length=24,
                    ),
                ),
                ("object_id", models.UUIDField()),
                ("alias", models.CharField(max_length=250)),
                (
                    "normalized_alias",
                    models.CharField(editable=False, max_length=250),
                ),
            ],
            options={
                "ordering": ("entity_type", "normalized_alias", "id"),
                "indexes": [
                    models.Index(
                        fields=["entity_type", "object_id"],
                        name="search_alias_entity_idx",
                    ),
                    django.contrib.postgres.indexes.GinIndex(
                        fields=["normalized_alias"],
                        name="search_alias_trgm_idx",
                        opclasses=("gin_trgm_ops",),
                    ),
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("entity_type", "object_id", "normalized_alias"),
                        name="search_alias_entity_value_unique",
                    )
                ],
            },
        ),
    ]
