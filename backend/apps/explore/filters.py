import django_filters

from apps.catalog.models import AudioTrack


class ExploreTrackFilter(django_filters.FilterSet):
    content_type = django_filters.CharFilter(field_name="content_type")
    contentType = django_filters.CharFilter(field_name="content_type")
    author = django_filters.CharFilter(field_name="work__author__slug")
    narrator = django_filters.CharFilter(field_name="narrator__slug")
    genre = django_filters.CharFilter(field_name="work__genres__slug")
    mood = django_filters.CharFilter(field_name="work__moods__slug")
    language = django_filters.CharFilter(field_name="language__slug")
    premium = django_filters.BooleanFilter(field_name="is_premium")
    explicit = django_filters.BooleanFilter(field_name="is_explicit")

    class Meta:
        model = AudioTrack
        fields = (
            "content_type",
            "contentType",
            "genre",
            "mood",
            "language",
            "author",
            "narrator",
            "premium",
            "explicit",
        )

    @property
    def qs(self):
        queryset = super().qs
        if self.is_valid() and (
            self.form.cleaned_data.get("genre") or self.form.cleaned_data.get("mood")
        ):
            return queryset.distinct()
        return queryset
