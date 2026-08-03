from django.db import migrations, models
import django.db.models.deletion


CATEGORY_NAMES = {
    "poem": ("कविता", "Poetry"),
    "story": ("कथा", "Story"),
    "essay": ("निबन्ध", "Essay"),
    "novel_chapter": ("उपन्यास", "Novel"),
    "folk_tale": ("लोककथा", "Folk tale"),
    "drama": ("नाटक", "Drama"),
}


def assign_categories(apps, schema_editor):
    ContentCategory = apps.get_model("taxonomy", "ContentCategory")
    LiteraryWork = apps.get_model("catalog", "LiteraryWork")

    for work in LiteraryWork.objects.all().iterator():
        name_ne, name_en = CATEGORY_NAMES.get(
            work.content_type,
            (work.content_type.replace("_", " ").title(), work.content_type),
        )
        category = ContentCategory.objects.filter(name_ne=name_ne).first()
        if category is None:
            category = ContentCategory.objects.create(
                name_ne=name_ne,
                name_en=name_en,
                slug=work.content_type,
                is_active=True,
            )
        work.category_id = category.id
        work.save(update_fields=("category",))


class Migration(migrations.Migration):
    dependencies = [
        ("taxonomy", "0001_initial"),
        ("catalog", "0014_alter_permissiondocument_document"),
    ]

    operations = [
        migrations.AddField(
            model_name="literarywork",
            name="category",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="literary_works",
                to="taxonomy.contentcategory",
            ),
        ),
        migrations.RunPython(assign_categories, migrations.RunPython.noop),
        migrations.RemoveIndex(
            model_name="literarywork",
            name="work_type_published_idx",
        ),
        migrations.RemoveIndex(
            model_name="audiotrack",
            name="track_type_published_idx",
        ),
        migrations.RemoveField(model_name="literarywork", name="content_type"),
        migrations.RemoveField(model_name="audiotrack", name="content_type"),
        migrations.AlterField(
            model_name="literarywork",
            name="category",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="literary_works",
                to="taxonomy.contentcategory",
            ),
        ),
        migrations.AddIndex(
            model_name="literarywork",
            index=models.Index(
                fields=("category", "is_published"),
                name="work_category_public_idx",
            ),
        ),
    ]
