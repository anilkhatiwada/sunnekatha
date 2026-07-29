from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("analytics", "0001_initial"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="dailyplatformmetric",
            options={
                "ordering": ("-date", "id"),
                "permissions": [
                    (
                        "export_analytics_dashboard",
                        "Can export aggregate analytics dashboard data",
                    )
                ],
            },
        ),
    ]
