from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("uploads", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="uploadsession",
            name="actual_size",
            field=models.PositiveBigIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="uploadsession",
            name="temporary_object_deleted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="uploadsession",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending"),
                    ("confirmed", "Confirmed"),
                    ("canceled", "Canceled"),
                    ("expired", "Expired"),
                    ("abandoned", "Abandoned"),
                ],
                db_index=True,
                default="pending",
                max_length=16,
            ),
        ),
    ]
