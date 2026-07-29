import django_filters

from apps.narrators.models import Narrator


class NarratorFilter(django_filters.FilterSet):
    featured = django_filters.BooleanFilter(field_name="is_featured")
    verified = django_filters.BooleanFilter(field_name="is_verified")

    class Meta:
        model = Narrator
        fields = ("featured", "verified")
