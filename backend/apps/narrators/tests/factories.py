import factory
from factory.django import DjangoModelFactory

from apps.narrators.models import Narrator


class NarratorFactory(DjangoModelFactory):
    class Meta:
        model = Narrator

    name_ne = factory.Sequence(lambda number: f"वाचक {number}")
    name_en = factory.Sequence(lambda number: f"Narrator {number}")
    biography_ne = "नेपाली जीवनी"
    biography_en = "English biography"
