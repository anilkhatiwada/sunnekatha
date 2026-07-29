import django_filters

from apps.authors.models import Author


class AuthorFilter(django_filters.FilterSet):
    featured = django_filters.BooleanFilter(field_name="is_featured")
    verified = django_filters.BooleanFilter(field_name="is_verified")

    class Meta:
        model = Author
        fields = ("featured", "verified")
