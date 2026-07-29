import factory
from factory.django import DjangoModelFactory

from apps.authors.models import Author


class AuthorFactory(DjangoModelFactory):
    class Meta:
        model = Author

    name_ne = factory.Sequence(lambda number: f"लेखक {number}")
    name_en = factory.Sequence(lambda number: f"Author {number}")
    biography_ne = "नेपाली जीवनी"
    biography_en = "English biography"
    country = "Nepal"
