from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0012_permission_document_management"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="audioprocessingjob",
            options={
                "ordering": ("-updated_at", "id"),
                "permissions": [
                    (
                        "retry_audioprocessingjob",
                        "Can retry failed audio processing jobs",
                    )
                ],
            },
        ),
        migrations.AlterModelOptions(
            name="permissiondocument",
            options={
                "ordering": ("title", "id"),
                "permissions": [
                    (
                        "verify_permissiondocument",
                        "Can verify and revoke permission document verification",
                    )
                ],
            },
        ),
    ]
