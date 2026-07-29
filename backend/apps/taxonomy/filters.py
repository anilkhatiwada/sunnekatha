import django_filters


class ActiveTaxonomyFilter(django_filters.FilterSet):
    active = django_filters.BooleanFilter(field_name="is_active")
