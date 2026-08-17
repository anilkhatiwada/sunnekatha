from io import BytesIO

import pytest
from django.contrib import admin
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image

from apps.accounts.tests.factories import UserFactory
from apps.taxonomy.admin import TaxonomyAdmin
from apps.taxonomy.models import ContentCategory, Genre, Language, Mood


@pytest.mark.parametrize("model", [Genre, Mood, Language, ContentCategory])
def test_taxonomy_models_are_registered_with_shared_admin(model):
    assert isinstance(admin.site._registry[model], TaxonomyAdmin)


@pytest.mark.django_db
def test_content_category_image_can_be_replaced_in_admin(client):
    user = UserFactory(is_staff=True, is_superuser=True)
    category = ContentCategory.objects.create(
        name_ne="कथा",
        name_en="Stories",
        description="",
        sort_order=1,
        is_active=True,
    )
    image_bytes = BytesIO()
    Image.new("RGB", (24, 24), color=(229, 138, 82)).save(
        image_bytes,
        format="JPEG",
    )
    upload = SimpleUploadedFile(
        "category.jpg",
        image_bytes.getvalue(),
        content_type="image/jpeg",
    )
    client.force_login(user)

    response = client.post(
        reverse("admin:taxonomy_contentcategory_change", args=(category.pk,)),
        {
            "name_ne": category.name_ne,
            "name_en": category.name_en,
            "description": category.description,
            "image": upload,
            "sort_order": category.sort_order,
            "is_active": "on",
        },
    )

    assert response.status_code == 302
    category.refresh_from_db()
    assert category.image.name.startswith(f"covers/contentcategory/{category.pk}/")
    assert category.image.name.endswith(".jpg")
