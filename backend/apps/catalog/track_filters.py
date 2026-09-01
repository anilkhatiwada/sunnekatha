import django_filters
from django.db.models import Q

from apps.catalog.models import AudioTrack


class AudioTrackFilter(django_filters.FilterSet):
    category = django_filters.CharFilter(method="filter_category")
    contentType = django_filters.CharFilter(method="filter_category")
    tag = django_filters.CharFilter(field_name="work__tags__slug", distinct=True)
    author = django_filters.CharFilter(field_name="work__author__slug")
    work = django_filters.CharFilter(field_name="work__slug")
    album = django_filters.CharFilter(field_name="album__slug")
    narrator = django_filters.CharFilter(field_name="narrator__slug")
    genre = django_filters.CharFilter(method="filter_genre")
    mood = django_filters.CharFilter(method="filter_mood")
    language = django_filters.CharFilter(field_name="language__slug")
    featured = django_filters.BooleanFilter(field_name="is_featured")
    premium = django_filters.BooleanFilter(field_name="is_premium")
    explicit = django_filters.BooleanFilter(field_name="is_explicit")

    class Meta:
        model = AudioTrack
        fields = (
            "contentType",
            "category",
            "author",
            "work",
            "album",
            "narrator",
            "genre",
            "mood",
            "tag",
            "language",
            "featured",
            "premium",
            "explicit",
        )

    def filter_category(self, queryset, name, value):
        del name
        return queryset.filter(
            Q(work__category__slug=value) | Q(work__categories__slug=value)
        ).distinct()

    def filter_genre(self, queryset, name, value):
        del name
        return queryset.filter(work__genres__slug=value).distinct()

    def filter_mood(self, queryset, name, value):
        del name
        return queryset.filter(work__moods__slug=value).distinct()
