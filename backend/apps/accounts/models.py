from django.contrib.auth.models import AbstractUser
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models.functions import Lower

from apps.accounts.managers import UserManager
from apps.common.models import UUIDTimeStampedModel
from apps.common.uploads import image_upload_path
from apps.common.validators import validate_image_upload


class PreferredLanguage(models.TextChoices):
    NEPALI = "ne", "Nepali"
    ENGLISH = "en", "English"


class User(UUIDTimeStampedModel, AbstractUser):
    email = models.EmailField(unique=True)
    display_name = models.CharField(max_length=100)
    avatar = models.ImageField(
        upload_to=image_upload_path,
        validators=[validate_image_upload],
        blank=True,
    )
    preferred_language = models.CharField(
        max_length=2,
        choices=PreferredLanguage.choices,
        default=PreferredLanguage.NEPALI,
    )
    default_playback_speed = models.FloatField(
        default=1.0,
        validators=[MinValueValidator(0.5), MaxValueValidator(2.0)],
    )
    autoplay_enabled = models.BooleanField(default=True)
    explicit_content_enabled = models.BooleanField(default=False)
    is_creator = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username", "display_name"]

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                Lower("email"),
                name="accounts_user_email_ci_unique",
            )
        ]

    def __str__(self):
        return self.display_name or self.email
