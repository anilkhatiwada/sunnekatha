import factory
from factory.django import DjangoModelFactory

from apps.accounts.models import User


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User

    email = factory.Sequence(lambda number: f"listener{number}@example.com")
    username = factory.Sequence(lambda number: f"listener{number}")
    display_name = factory.Sequence(lambda number: f"Listener {number}")
    password = "StrongPass!234"

    class Params:
        creator = factory.Trait(is_creator=True)
        staff = factory.Trait(is_staff=True)

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        return model_class.objects.create_user(*args, **kwargs)
