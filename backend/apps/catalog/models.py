from datetime import date

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from apps.authors.models import Author
from apps.common.models import UUIDTimeStampedModel
from apps.common.slugs import generate_unique_slug
from apps.common.storage import original_audio_storage, processed_audio_storage
from apps.common.uploads import (
    image_upload_path,
    original_audio_upload_path,
    permission_document_upload_path,
    processed_audio_upload_path,
)
from apps.common.validators import (
    validate_audio_upload,
    validate_image_upload,
    validate_permission_document_upload,
)
from apps.narrators.models import Narrator
from apps.taxonomy.models import ContentCategory, Genre, Language, Mood


class CopyrightStatus(models.TextChoices):
    COPYRIGHTED = "copyrighted", "Copyrighted"
    LICENSED = "licensed", "Licensed"
    PERMISSION_GRANTED = "permission_granted", "Permission granted"
    PUBLIC_DOMAIN = "public_domain", "Public domain"
    PERMISSION_PENDING = "permission_pending", "Permission pending"
    PERMISSION_EXPIRED = "permission_expired", "Permission expired"
    PERMISSION_REJECTED = "permission_rejected", "Permission rejected"
    OWNERSHIP_UNCLEAR = "ownership_unclear", "Ownership unclear"
    UNKNOWN = "unknown", "Unknown (legacy)"


class RightsPermissionType(models.TextChoices):
    AUDIO = "audio", "Audio adaptation"
    COMMERCIAL = "commercial", "Commercial use"
    AUDIO_COMMERCIAL = "audio_commercial", "Audio and commercial use"
    DISTRIBUTION = "distribution", "Distribution"
    OTHER = "other", "Other"


class RightsVerificationStatus(models.TextChoices):
    UNVERIFIED = "unverified", "Unverified"
    PENDING = "pending", "Pending verification"
    VERIFIED = "verified", "Verified"
    REJECTED = "rejected", "Verification rejected"


class PermissionDocumentType(models.TextChoices):
    LICENSE = "license", "License agreement"
    CONSENT = "consent", "Consent letter"
    OWNERSHIP = "ownership", "Ownership evidence"
    PUBLIC_DOMAIN = "public_domain", "Public-domain evidence"
    OTHER = "other", "Other"


class PermissionDocumentAuditAction(models.TextChoices):
    VERIFIED = "verified", "Verified"
    VERIFICATION_REVOKED = "verification_revoked", "Verification revoked"
    DOWNLOADED = "downloaded", "Downloaded"


class AlbumType(models.TextChoices):
    COLLECTION = "collection", "Collection"
    ANTHOLOGY = "anthology", "Anthology"
    AUDIOBOOK = "audiobook", "Audiobook"
    SERIES = "series", "Series"


class TrackProcessingStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    PROCESSING = "processing", "Processing"
    READY = "ready", "Ready"
    FAILED = "failed", "Failed"


class TrackReviewStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    SUBMITTED = "submitted", "Submitted"
    CHANGES_REQUESTED = "changes_requested", "Changes requested"
    APPROVED = "approved", "Approved"
    SCHEDULED = "scheduled", "Scheduled"
    PUBLISHED = "published", "Published"
    REJECTED = "rejected", "Rejected"
    ARCHIVED = "archived", "Archived"


class AudioProcessingJobStatus(models.TextChoices):
    QUEUED = "queued", "Queued"
    PROCESSING = "processing", "Processing"
    READY = "ready", "Ready"
    FAILED = "failed", "Failed"


class AudioProcessingStage(models.TextChoices):
    UPLOAD = "upload", "Upload validation"
    TRANSCODING = "transcoding", "Audio transcoding"
    WAVEFORM = "waveform", "Waveform generation"
    METADATA = "metadata", "Metadata extraction"
    FINALIZING = "finalizing", "Finalizing"


class LiteraryWorkQuerySet(models.QuerySet):
    def published(self):
        return self.filter(
            is_published=True,
            published_at__lte=timezone.now(),
        )


class AlbumQuerySet(models.QuerySet):
    def published(self):
        return self.filter(is_published=True)


class AudioTrackQuerySet(models.QuerySet):
    def published(self):
        return self.filter(
            is_published=True,
            processing_status=TrackProcessingStatus.READY,
            published_at__lte=timezone.now(),
        )


class LiteraryWork(UUIDTimeStampedModel):
    slug = models.SlugField(max_length=220, unique=True, allow_unicode=True)
    title_ne = models.CharField(max_length=250)
    title_en = models.CharField(max_length=250, blank=True)
    subtitle_ne = models.CharField(max_length=300, blank=True)
    subtitle_en = models.CharField(max_length=300, blank=True)
    description_ne = models.TextField(blank=True)
    description_en = models.TextField(blank=True)
    category = models.ForeignKey(
        ContentCategory,
        related_name="literary_works",
        on_delete=models.PROTECT,
    )
    author = models.ForeignKey(
        Author,
        related_name="literary_works",
        on_delete=models.PROTECT,
    )
    language = models.ForeignKey(
        Language,
        related_name="literary_works",
        on_delete=models.PROTECT,
    )
    genres = models.ManyToManyField(Genre, related_name="literary_works", blank=True)
    moods = models.ManyToManyField(Mood, related_name="literary_works", blank=True)
    publication_year = models.PositiveSmallIntegerField(
        blank=True,
        null=True,
        validators=[MinValueValidator(1000)],
    )
    copyright_status = models.CharField(
        max_length=24,
        choices=CopyrightStatus.choices,
        default=CopyrightStatus.OWNERSHIP_UNCLEAR,
    )
    copyright_owner = models.CharField(max_length=250, blank=True)
    license_notes = models.TextField(blank=True)
    cover_image = models.ImageField(
        upload_to=image_upload_path,
        validators=[validate_image_upload],
        blank=True,
    )
    is_featured = models.BooleanField(default=False, db_index=True)
    is_published = models.BooleanField(default=False, db_index=True)
    published_at = models.DateTimeField(blank=True, null=True, db_index=True)

    objects = LiteraryWorkQuerySet.as_manager()

    class Meta:
        ordering = ("-published_at", "title_ne", "id")
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(is_published=False) | models.Q(published_at__isnull=False)
                ),
                name="work_published_requires_timestamp",
            )
        ]
        indexes = [
            models.Index(
                fields=("is_published", "is_featured", "-published_at"),
                name="work_public_featured_idx",
            ),
            models.Index(
                fields=("category", "is_published"),
                name="work_category_public_idx",
            ),
        ]

    def clean(self):
        super().clean()
        if self.publication_year and self.publication_year > date.today().year:
            raise ValidationError(
                {"publication_year": "Publication year cannot be in the future."}
            )
        if self.is_published and self.published_at is None:
            raise ValidationError(
                {"published_at": "Published content requires a publication time."}
            )

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(
                self,
                self.title_ne,
                fallback="literary-work",
            )
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title_ne


class Album(UUIDTimeStampedModel):
    slug = models.SlugField(max_length=220, unique=True, allow_unicode=True)
    title_ne = models.CharField(max_length=250)
    title_en = models.CharField(max_length=250, blank=True)
    description_ne = models.TextField(blank=True)
    description_en = models.TextField(blank=True)
    cover_image = models.ImageField(
        upload_to=image_upload_path,
        validators=[validate_image_upload],
        blank=True,
    )
    author = models.ForeignKey(
        Author,
        related_name="albums",
        on_delete=models.PROTECT,
    )
    album_type = models.CharField(
        max_length=24,
        choices=AlbumType.choices,
        default=AlbumType.COLLECTION,
    )
    genres = models.ManyToManyField(Genre, related_name="albums", blank=True)
    moods = models.ManyToManyField(Mood, related_name="albums", blank=True)
    release_date = models.DateField(blank=True, null=True)
    is_featured = models.BooleanField(default=False, db_index=True)
    is_published = models.BooleanField(default=False, db_index=True)

    objects = AlbumQuerySet.as_manager()

    class Meta:
        ordering = ("-release_date", "title_ne", "id")
        indexes = [
            models.Index(
                fields=("is_published", "is_featured", "-release_date"),
                name="album_public_featured_idx",
            )
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(self, self.title_ne, fallback="album")
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title_ne


class AudioTrack(UUIDTimeStampedModel):
    slug = models.SlugField(max_length=220, unique=True, allow_unicode=True)
    work = models.ForeignKey(
        LiteraryWork,
        related_name="audio_tracks",
        on_delete=models.PROTECT,
    )
    album = models.ForeignKey(
        Album,
        related_name="audio_tracks",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    chapter_number = models.PositiveIntegerField(blank=True, null=True)
    track_number = models.PositiveIntegerField(blank=True, null=True)
    title_ne = models.CharField(max_length=250)
    title_en = models.CharField(max_length=250, blank=True)
    description_ne = models.TextField(blank=True)
    description_en = models.TextField(blank=True)
    narrator = models.ForeignKey(
        Narrator,
        related_name="audio_tracks",
        on_delete=models.PROTECT,
    )
    language = models.ForeignKey(
        Language,
        related_name="audio_tracks",
        on_delete=models.PROTECT,
    )
    duration_seconds = models.PositiveIntegerField(default=0)
    audio_master_file = models.FileField(
        upload_to=original_audio_upload_path,
        storage=original_audio_storage,
        validators=[validate_audio_upload],
        blank=True,
    )
    stream_file_high = models.FileField(
        upload_to=processed_audio_upload_path,
        storage=processed_audio_storage,
        validators=[validate_audio_upload],
        blank=True,
    )
    stream_file_low = models.FileField(
        upload_to=processed_audio_upload_path,
        storage=processed_audio_storage,
        validators=[validate_audio_upload],
        blank=True,
    )
    waveform_data = models.JSONField(default=list, blank=True)
    transcript = models.TextField(blank=True)
    is_explicit = models.BooleanField(default=False)
    is_premium = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False, db_index=True)
    is_published = models.BooleanField(default=False, db_index=True)
    processing_status = models.CharField(
        max_length=16,
        choices=TrackProcessingStatus.choices,
        default=TrackProcessingStatus.PENDING,
        db_index=True,
    )
    review_status = models.CharField(
        max_length=24,
        choices=TrackReviewStatus.choices,
        default=TrackReviewStatus.DRAFT,
        db_index=True,
    )
    submitted_at = models.DateTimeField(blank=True, null=True)
    reviewed_at = models.DateTimeField(blank=True, null=True)
    reviewed_by = models.ForeignKey(
        "accounts.User",
        related_name="tracks_reviewed",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    review_comments = models.TextField(blank=True)
    published_at = models.DateTimeField(blank=True, null=True, db_index=True)
    play_count_cache = models.PositiveBigIntegerField(default=0)
    objects = AudioTrackQuerySet.as_manager()

    class Meta:
        ordering = ("album_id", "track_number", "chapter_number", "title_ne", "id")
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(is_published=False)
                    | (
                        models.Q(published_at__isnull=False)
                        & models.Q(processing_status=TrackProcessingStatus.READY)
                    )
                ),
                name="track_publish_requires_ready_timestamp",
            )
        ]
        indexes = [
            models.Index(
                fields=("is_published", "is_featured", "-published_at"),
                name="track_public_featured_idx",
            ),
            models.Index(
                fields=("narrator", "is_published", "-published_at"),
                name="track_narrator_public_idx",
            ),
            models.Index(
                fields=("work", "track_number"),
                name="track_work_order_idx",
            ),
            models.Index(
                fields=("album", "track_number"),
                name="track_album_order_idx",
            ),
        ]
        permissions = [
            ("approve_audiotrack", "Can approve audio track submissions"),
            ("publish_audiotrack", "Can schedule and publish audio tracks"),
            (
                "approve_own_audiotrack",
                "Can approve own audio track submissions",
            ),
        ]

    def clean(self):
        super().clean()
        errors = {}
        if (
            self.album_id
            and self.work_id
            and self.album.author_id != self.work.author_id
        ):
            errors["album"] = "Album and literary work must have the same author."
        if self.is_published and self.published_at is None:
            errors["published_at"] = "Published tracks require a publication time."
        if self.is_published and self.processing_status != TrackProcessingStatus.READY:
            errors["processing_status"] = "Only ready tracks can be published."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(
                self, self.title_ne, fallback="audio-track"
            )
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title_ne


class TrackReviewEvent(UUIDTimeStampedModel):
    track = models.ForeignKey(
        AudioTrack,
        related_name="review_events",
        on_delete=models.CASCADE,
    )
    from_status = models.CharField(max_length=24, choices=TrackReviewStatus.choices)
    to_status = models.CharField(max_length=24, choices=TrackReviewStatus.choices)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="track_review_events",
        on_delete=models.PROTECT,
    )
    comment = models.TextField(blank=True)
    scheduled_for = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ("-created_at", "-id")
        indexes = [
            models.Index(
                fields=("track", "-created_at"),
                name="track_review_event_track_idx",
            )
        ]

    def __str__(self):
        return f"{self.track}: {self.from_status} → {self.to_status}"


class PendingReviewTrack(AudioTrack):
    class Meta:
        proxy = True
        verbose_name = "Pending review"
        verbose_name_plural = "Pending reviews"


class RightsHolder(UUIDTimeStampedModel):
    name = models.CharField(max_length=250)
    contact_email = models.EmailField(blank=True)
    country = models.CharField(max_length=120, blank=True)
    notes = models.TextField(blank=True)
    is_verified = models.BooleanField(default=False, db_index=True)

    class Meta:
        ordering = ("name", "id")

    def __str__(self):
        return self.name


class CopyrightLicense(UUIDTimeStampedModel):
    literary_work = models.ForeignKey(
        LiteraryWork,
        related_name="copyright_licenses",
        on_delete=models.CASCADE,
    )
    rights_holder = models.ForeignKey(
        RightsHolder,
        related_name="licenses",
        on_delete=models.PROTECT,
        blank=True,
        null=True,
    )
    permission_type = models.CharField(
        max_length=24,
        choices=RightsPermissionType.choices,
    )
    effective_date = models.DateField(blank=True, null=True, db_index=True)
    expiration_date = models.DateField(blank=True, null=True, db_index=True)
    territory = models.CharField(max_length=250, blank=True)
    allows_monetization = models.BooleanField(default=False)
    allows_audio = models.BooleanField(default=False)
    verification_status = models.CharField(
        max_length=16,
        choices=RightsVerificationStatus.choices,
        default=RightsVerificationStatus.UNVERIFIED,
        db_index=True,
    )
    internal_notes = models.TextField(blank=True)

    class Meta:
        ordering = ("expiration_date", "literary_work__title_ne", "id")
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(effective_date__isnull=True)
                    | models.Q(expiration_date__isnull=True)
                    | models.Q(expiration_date__gte=models.F("effective_date"))
                ),
                name="copyright_license_valid_dates",
            )
        ]
        indexes = [
            models.Index(
                fields=("verification_status", "expiration_date"),
                name="rights_verify_expiry_idx",
            )
        ]

    def clean(self):
        super().clean()
        if (
            self.effective_date
            and self.expiration_date
            and self.expiration_date < self.effective_date
        ):
            raise ValidationError(
                {"expiration_date": "Expiration cannot precede the effective date."}
            )

    def __str__(self):
        return f"{self.literary_work} — {self.get_permission_type_display()}"


class PermissionDocument(UUIDTimeStampedModel):
    license = models.ForeignKey(
        CopyrightLicense,
        related_name="documents",
        on_delete=models.CASCADE,
    )
    title = models.CharField(max_length=250)
    document_type = models.CharField(
        max_length=24,
        choices=PermissionDocumentType.choices,
        default=PermissionDocumentType.LICENSE,
    )
    document = models.FileField(
        upload_to=permission_document_upload_path,
        storage=original_audio_storage,
        validators=[validate_permission_document_upload],
    )
    is_verified = models.BooleanField(default=False, db_index=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="rights_documents_uploaded",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="rights_documents_verified",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    verified_at = models.DateTimeField(blank=True, null=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ("title", "id")
        permissions = [
            (
                "verify_permissiondocument",
                "Can verify and revoke permission document verification",
            )
        ]

    def __str__(self):
        return self.title


class PermissionDocumentAudit(UUIDTimeStampedModel):
    document = models.ForeignKey(
        PermissionDocument,
        related_name="audit_events",
        on_delete=models.CASCADE,
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="permission_document_audits",
        on_delete=models.PROTECT,
    )
    action = models.CharField(
        max_length=24,
        choices=PermissionDocumentAuditAction.choices,
        db_index=True,
    )
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ("-created_at", "-id")
        indexes = [
            models.Index(
                fields=("document", "-created_at"),
                name="permission_doc_audit_idx",
            )
        ]

    def __str__(self):
        return f"{self.document}: {self.get_action_display()}"


class AudioProcessingJob(UUIDTimeStampedModel):
    track = models.OneToOneField(
        AudioTrack,
        related_name="processing_job",
        on_delete=models.CASCADE,
    )
    upload_session = models.ForeignKey(
        "uploads.UploadSession",
        related_name="processing_jobs",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    status = models.CharField(
        max_length=16,
        choices=AudioProcessingJobStatus.choices,
        default=AudioProcessingJobStatus.QUEUED,
        db_index=True,
    )
    stage = models.CharField(
        max_length=24,
        choices=AudioProcessingStage.choices,
        default=AudioProcessingStage.UPLOAD,
        db_index=True,
    )
    error_summary = models.CharField(max_length=500, blank=True)
    technical_error = models.TextField(blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    max_attempts = models.PositiveSmallIntegerField(default=3)
    last_attempt_at = models.DateTimeField(blank=True, null=True, db_index=True)
    retry_initiated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="initiated_audio_processing_retries",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    retry_requested_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ("-updated_at", "id")
        permissions = [
            (
                "retry_audioprocessingjob",
                "Can retry failed audio processing jobs",
            )
        ]
        indexes = [
            models.Index(
                fields=("status", "stage", "-last_attempt_at"),
                name="audio_job_status_stage_idx",
            )
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(max_attempts__gt=0),
                name="audio_job_max_attempts_positive",
            ),
            models.CheckConstraint(
                condition=models.Q(attempts__lte=models.F("max_attempts")),
                name="audio_job_attempts_within_max",
            ),
        ]

    @property
    def retry_available(self):
        return (
            self.status == AudioProcessingJobStatus.FAILED
            and self.attempts < self.max_attempts
        )

    @property
    def admin_processing_state(self):
        if self.track.is_published:
            return "published"
        return self.status

    def __str__(self):
        return f"{self.track} — {self.get_status_display()}"
