import django_filters

from apps.catalog.models import AudioTrack


class AudioTrackFilter(django_filters.FilterSet):
    contentType = django_filters.CharFilter(field_name="content_type")
    author = django_filters.CharFilter(field_name="work__author__slug")
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
            "author",
            "narrator",
            "genre",
            "mood",
            "language",
            "featured",
            "premium",
            "explicit",
        )

    def filter_genre(self, queryset, name, value):
        del name
        return queryset.filter(work__genres__slug=value).distinct()

    def filter_mood(self, queryset, name, value):
        del name
        return queryset.filter(work__moods__slug=value).distinct()
