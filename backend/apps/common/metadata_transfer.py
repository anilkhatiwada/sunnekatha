import csv
from dataclasses import dataclass
from io import StringIO

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.authors.models import Author
from apps.catalog.models import AudioTrack, CopyrightLicense, LiteraryWork
from apps.common.audit import administrative_audit_service
from apps.common.models import AdministrativeAuditAction
from apps.narrators.models import Narrator
from apps.playlists.models import Playlist
from apps.taxonomy.models import ContentCategory, Genre, Language, Mood

MAX_IMPORT_BYTES = 1024 * 1024
MAX_IMPORT_ROWS = 500

EXPORT_FIELDS = {
    "authors": (
        "id",
        "slug",
        "name_ne",
        "name_en",
        "birth_date",
        "death_date",
        "country",
        "is_featured",
        "is_verified",
    ),
    "narrators": (
        "id",
        "slug",
        "name_ne",
        "name_en",
        "is_featured",
        "is_verified",
        "follower_count_cache",
    ),
    "literary_works": (
        "id",
        "slug",
        "title_ne",
        "title_en",
        "category_slug",
        "author_slug",
        "language_slug",
        "publication_year",
        "copyright_status",
        "copyright_owner",
        "is_featured",
        "is_published",
        "published_at",
    ),
    "tracks": (
        "id",
        "slug",
        "title_ne",
        "title_en",
        "work_slug",
        "narrator_slug",
        "processing_status",
        "review_status",
        "duration_seconds",
        "is_premium",
        "is_explicit",
        "is_featured",
        "is_published",
        "published_at",
    ),
    "playlists": (
        "id",
        "slug",
        "title_ne",
        "title_en",
        "playlist_type",
        "visibility",
        "owner_email",
        "is_featured",
        "is_published",
    ),
    "copyright_records": (
        "id",
        "literary_work_slug",
        "rights_holder",
        "permission_type",
        "effective_date",
        "expiration_date",
        "territory",
        "allows_monetization",
        "allows_audio",
        "verification_status",
    ),
}

IMPORT_FIELDS = {
    "authors": (
        "slug",
        "name_ne",
        "name_en",
        "biography_ne",
        "biography_en",
        "birth_date",
        "death_date",
        "country",
    ),
    "narrators": (
        "slug",
        "name_ne",
        "name_en",
        "biography_ne",
        "biography_en",
    ),
    "genres": ("slug", "name_ne", "name_en", "description", "sort_order"),
    "moods": ("slug", "name_ne", "name_en", "description", "sort_order"),
    "literary_works": (
        "slug",
        "title_ne",
        "title_en",
        "subtitle_ne",
        "subtitle_en",
        "description_ne",
        "description_en",
        "category_slug",
        "author_slug",
        "language_slug",
        "genre_slugs",
        "mood_slugs",
        "publication_year",
        "copyright_status",
        "copyright_owner",
        "license_notes",
    ),
}

MODEL_BY_EXPORT = {
    "authors": Author,
    "narrators": Narrator,
    "literary_works": LiteraryWork,
    "tracks": AudioTrack,
    "playlists": Playlist,
    "copyright_records": CopyrightLicense,
}

MODEL_BY_IMPORT = {
    "authors": Author,
    "narrators": Narrator,
    "genres": Genre,
    "moods": Mood,
    "literary_works": LiteraryWork,
}


@dataclass(frozen=True)
class RowError:
    row: int
    messages: tuple[str, ...]


@dataclass(frozen=True)
class ImportPreview:
    kind: str
    rows: tuple[dict, ...]
    errors: tuple[RowError, ...]

    @property
    def is_valid(self):
        return not self.errors


def _serialize(value):
    if value is None:
        return ""
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def _export_value(obj, field):
    relations = {
        "author_slug": lambda: obj.author.slug,
        "language_slug": lambda: obj.language.slug,
        "category_slug": lambda: obj.category.slug,
        "work_slug": lambda: obj.work.slug,
        "narrator_slug": lambda: obj.narrator.slug,
        "owner_email": lambda: obj.owner.email if obj.owner_id else "",
        "literary_work_slug": lambda: obj.literary_work.slug,
        "rights_holder": lambda: obj.rights_holder.name if obj.rights_holder_id else "",
    }
    return _serialize(relations[field]() if field in relations else getattr(obj, field))


def export_csv(kind):
    model = MODEL_BY_EXPORT[kind]
    fields = EXPORT_FIELDS[kind]
    queryset = model._base_manager.all().order_by("pk")
    if kind == "literary_works":
        queryset = queryset.select_related("author", "language")
    elif kind == "tracks":
        queryset = queryset.select_related("work", "narrator")
    elif kind == "playlists":
        queryset = queryset.select_related("owner")
    elif kind == "copyright_records":
        queryset = queryset.select_related("literary_work", "rights_holder")
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(fields)
    for obj in queryset.iterator(chunk_size=500):
        writer.writerow([_export_value(obj, field) for field in fields])
    return output.getvalue(), queryset.count()


def _split_slugs(value):
    return tuple(item.strip() for item in value.split(",") if item.strip())


def _normalize_row(kind, raw):
    allowed = IMPORT_FIELDS[kind]
    row = {field: (raw.get(field) or "").strip() for field in allowed}
    if kind == "authors":
        row["birth_date"] = row["birth_date"] or None
        row["death_date"] = row["death_date"] or None
    if kind in {"genres", "moods"}:
        row["sort_order"] = int(row["sort_order"] or 0)
    if kind == "literary_works":
        row["publication_year"] = (
            int(row["publication_year"]) if row["publication_year"] else None
        )
        row["genre_slugs"] = _split_slugs(row["genre_slugs"])
        row["mood_slugs"] = _split_slugs(row["mood_slugs"])
    return row


def _build(kind, row):
    if kind == "authors":
        return Author(**row), {}
    if kind == "narrators":
        return Narrator(**row), {}
    if kind in {"genres", "moods"}:
        return MODEL_BY_IMPORT[kind](**row), {}
    author = Author.objects.get(slug=row["author_slug"])
    language = Language.objects.get(slug=row["language_slug"])
    category = ContentCategory.objects.get(slug=row["category_slug"])
    genres = list(Genre.objects.filter(slug__in=row["genre_slugs"]))
    moods = list(Mood.objects.filter(slug__in=row["mood_slugs"]))
    missing_genres = set(row["genre_slugs"]) - {item.slug for item in genres}
    missing_moods = set(row["mood_slugs"]) - {item.slug for item in moods}
    if missing_genres or missing_moods:
        raise ValidationError(
            f"Unknown genres: {sorted(missing_genres)}; "
            f"unknown moods: {sorted(missing_moods)}"
        )
    values = {
        key: value
        for key, value in row.items()
        if key not in {
            "author_slug",
            "language_slug",
            "category_slug",
            "genre_slugs",
            "mood_slugs",
        }
    }
    return (
        LiteraryWork(
            **values,
            author=author,
            language=language,
            category=category,
            is_published=False,
            published_at=None,
        ),
        {"genres": genres, "moods": moods},
    )


def preview_import(kind, content):
    if kind not in IMPORT_FIELDS:
        raise ValidationError("Unsupported import type.")
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValidationError("CSV must be UTF-8 encoded.") from exc
    reader = csv.DictReader(StringIO(text))
    if not reader.fieldnames:
        raise ValidationError("CSV header row is required.")
    forbidden = [
        name
        for name in reader.fieldnames
        if any(term in name.lower() for term in ("audio", "image", "file", "cover"))
    ]
    if forbidden:
        raise ValidationError(
            "File and media columns are not accepted: "
            + ", ".join(sorted(forbidden))
            + "."
        )
    missing = set(IMPORT_FIELDS[kind]) - set(reader.fieldnames)
    if missing:
        raise ValidationError(f"Missing columns: {', '.join(sorted(missing))}.")
    rows = []
    errors = []
    seen_slugs = set()
    for number, raw in enumerate(reader, start=2):
        if number > MAX_IMPORT_ROWS + 1:
            raise ValidationError(f"CSV cannot exceed {MAX_IMPORT_ROWS} rows.")
        try:
            row = _normalize_row(kind, raw)
            if not row["slug"]:
                raise ValidationError("Slug is required.")
            if row["slug"] in seen_slugs:
                raise ValidationError("Duplicate slug within this CSV.")
            seen_slugs.add(row["slug"])
            obj, _relations = _build(kind, row)
            obj.full_clean(validate_unique=True)
        except (
            ValueError,
            ValidationError,
            Author.DoesNotExist,
            Language.DoesNotExist,
        ) as exc:
            messages = (
                tuple(exc.messages) if isinstance(exc, ValidationError) else (str(exc),)
            )
            errors.append(RowError(number, messages))
        rows.append(row)
    if not rows:
        errors.append(RowError(1, ("CSV contains no data rows.",)))
    return ImportPreview(kind, tuple(rows), tuple(errors))


@transaction.atomic
def commit_import(preview, *, actor):
    if not preview.is_valid:
        raise ValidationError("Import contains validation errors.")
    created = []
    for row in preview.rows:
        obj, relations = _build(preview.kind, row)
        obj.full_clean(validate_unique=True)
        obj.save()
        for field, values in relations.items():
            getattr(obj, field).set(values)
        created.append(obj)
        administrative_audit_service.record(
            actor=actor,
            action=AdministrativeAuditAction.METADATA_IMPORTED,
            obj=obj,
            reason=f"Created through confirmed {preview.kind} CSV import.",
        )
    return created
