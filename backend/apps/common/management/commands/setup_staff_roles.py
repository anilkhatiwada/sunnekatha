from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.common.staff_roles import ROLE_PERMISSIONS


class Command(BaseCommand):
    help = (
        "Create or update SunneKatha staff groups additively. "
        "Existing custom group permissions are preserved."
    )

    @transaction.atomic
    def handle(self, *args, **options):
        available = {
            f"{permission.content_type.app_label}.{permission.codename}": permission
            for permission in Permission.objects.select_related("content_type")
        }
        required = set().union(*ROLE_PERMISSIONS.values())
        missing = sorted(required - available.keys())
        if missing:
            raise CommandError(
                "Required permissions are missing. Apply migrations first: "
                + ", ".join(missing)
            )

        for role_name, permission_names in ROLE_PERMISSIONS.items():
            group, created = Group.objects.get_or_create(name=role_name)
            permissions = [available[name] for name in sorted(permission_names)]
            before = group.permissions.count()
            group.permissions.add(*permissions)
            added = group.permissions.count() - before
            state = "created" if created else "updated"
            self.stdout.write(
                f"{role_name}: {state}; added {added}; "
                f"{group.permissions.count()} total permission(s)"
            )

        self.stdout.write(
            self.style.SUCCESS(
                "SunneKatha staff roles are ready. Existing permissions were preserved."
            )
        )
