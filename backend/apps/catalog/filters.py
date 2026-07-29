import django_filters

from apps.catalog.models import Album, LiteraryWork


class CatalogRelationFilterMixin:
    def filter_genre(self, queryset, name, value):
        del name
        return queryset.filter(genres__slug=value).distinct()

    def filter_mood(self, queryset, name, value):
        del name
        return queryset.filter(moods__slug=value).distinct()


class LiteraryWorkFilter(CatalogRelationFilterMixin, django_filters.FilterSet):
    contentType = django_filters.CharFilter(field_name="content_type")
    author = django_filters.CharFilter(field_name="author__slug")
    genre = django_filters.CharFilter(method="filter_genre")
    mood = django_filters.CharFilter(method="filter_mood")
    language = django_filters.CharFilter(field_name="language__slug")
    featured = django_filters.BooleanFilter(field_name="is_featured")
    published = django_filters.BooleanFilter(field_name="is_published")

    class Meta:
        model = LiteraryWork
        fields = (
            "contentType",
            "author",
            "genre",
            "mood",
            "language",
            "featured",
            "published",
        )


class AlbumFilter(CatalogRelationFilterMixin, django_filters.FilterSet):
    author = django_filters.CharFilter(field_name="author__slug")
    genre = django_filters.CharFilter(method="filter_genre")
    mood = django_filters.CharFilter(method="filter_mood")
    featured = django_filters.BooleanFilter(field_name="is_featured")
    published = django_filters.BooleanFilter(field_name="is_published")

    class Meta:
        model = Album
        fields = ("author", "genre", "mood", "featured", "published")
