from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("catalog", "0010_rights_management")]

    operations = [
        migrations.AlterField(
            model_name="literarywork",
            name="copyright_status",
            field=models.CharField(
                choices=[
                    ("copyrighted", "Copyrighted"),
                    ("licensed", "Licensed"),
                    ("permission_granted", "Permission granted"),
                    ("public_domain", "Public domain"),
                    ("permission_pending", "Permission pending"),
                    ("permission_expired", "Permission expired"),
                    ("permission_rejected", "Permission rejected"),
                    ("ownership_unclear", "Ownership unclear"),
                    ("unknown", "Unknown (legacy)"),
                ],
                default="ownership_unclear",
                max_length=24,
            ),
        )
    ]
