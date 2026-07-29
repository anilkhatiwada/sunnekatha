from django.apps import AppConfig


class HomeConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.home"

    def ready(self):
        from apps.home import signals  # noqa: F401
