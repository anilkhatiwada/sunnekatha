from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("home", "0003_remove_homesectionitem_home_section_item_exactly_one_target_and_more"), ("taxonomy", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="homesection",
            name="content_source",
            field=models.CharField(
                choices=[
                    ("editorial", "Selected editorial items"),
                    ("recent_releases", "Automatic new releases"),
                ],
                default="editorial",
                max_length=24,
            ),
        ),
        migrations.AddField(
            model_name="homesection",
            name="browse_category",
            field=models.ForeignKey(
                blank=True,
                help_text="Optional category used by track sections for their See all link.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="homepage_track_sections",
                to="taxonomy.contentcategory",
            ),
        ),
    ]
