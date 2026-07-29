from django.core.management.base import BaseCommand
from django.db import transaction

from apps.taxonomy.models import ContentCategory, Genre, Language, Mood

GENRES = [
    ("poetry", "कविता", "Poetry", "भावना, लय र बिम्बमा रचिएका कविता।"),
    ("short-story", "कथा", "Stories", "छोटो र लामो आख्यानका श्रव्य प्रस्तुति।"),
    ("essay", "निबन्ध", "Essays", "विचार र अनुभवमा आधारित निबन्ध।"),
    ("novel", "उपन्यास", "Novels", "क्रमिक अध्यायमा प्रस्तुत लामो आख्यान।"),
    ("folk-tale", "लोककथा", "Folk tales", "नेपाली मौखिक परम्पराका कथा।"),
    ("drama", "नाटक", "Drama", "संवाद र अभिनयमा आधारित प्रस्तुति।"),
    ("children", "बालसाहित्य", "Children's literature", "बालमनका लागि रचना।"),
]

MOODS = [
    ("romantic", "प्रेम", "Romance", "माया र आत्मीयताले भरिएका रचना।"),
    ("philosophy", "दर्शन", "Philosophy", "जीवनका प्रश्नमाथि चिन्तन।"),
    ("inspiration", "प्रेरणा", "Inspiration", "साहस र सुरुवातका लागि प्रेरणा।"),
    ("rain", "वर्षा", "Rain", "वर्षाको अनुभूतिसँग सुहाउने सामग्री।"),
    ("calm", "शान्ति", "Calm", "मनलाई शान्त बनाउने वाचन।"),
    ("longing", "विरह", "Longing", "दूरी र सम्झनाका भाव बोकेका रचना।"),
]

LANGUAGES = [
    ("ne", "नेपाली", "Nepali", "नेपाली भाषामा उपलब्ध सामग्री।"),
    ("en", "अङ्ग्रेजी", "English", "Content available in English."),
]

CONTENT_CATEGORIES = [
    ("poem", "कविता", "Poem", "कविता विधाका श्रव्य रचना।"),
    ("story", "कथा", "Story", "कथा विधाका श्रव्य रचना।"),
    ("essay", "निबन्ध", "Essay", "निबन्ध विधाका श्रव्य रचना।"),
    ("novel", "उपन्यास", "Novel", "उपन्यास र यसका अध्याय।"),
    ("folk-tale", "लोककथा", "Folk tale", "लोकपरम्परामा आधारित कथा।"),
    ("drama", "नाटक", "Drama", "श्रव्य नाट्य प्रस्तुति।"),
    ("children", "बालसाहित्य", "Children", "बालबालिकाका लागि सामग्री।"),
]

SEED_GROUPS = (
    (Genre, GENRES),
    (Mood, MOODS),
    (Language, LANGUAGES),
    (ContentCategory, CONTENT_CATEGORIES),
)


class Command(BaseCommand):
    help = "Create or update the standard SunneKatha catalog taxonomies."

    @transaction.atomic
    def handle(self, *args, **options):
        del args, options
        created_count = 0
        updated_count = 0

        for model, records in SEED_GROUPS:
            for sort_order, (slug, name_ne, name_en, description) in enumerate(records):
                _, created = model.objects.update_or_create(
                    slug=slug,
                    defaults={
                        "name_ne": name_ne,
                        "name_en": name_en,
                        "description": description,
                        "sort_order": sort_order,
                        "is_active": True,
                    },
                )
                created_count += int(created)
                updated_count += int(not created)

        self.stdout.write(
            self.style.SUCCESS(
                f"Taxonomies seeded: {created_count} created, {updated_count} updated."
            )
        )
