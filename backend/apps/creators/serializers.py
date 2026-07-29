from rest_framework import serializers

from apps.catalog.models import AudioTrack, CopyrightStatus, TrackReviewStatus
from apps.catalog.track_serializers import CompactTrackSerializer
from apps.common.serializers import RejectUnknownFieldsMixin
from apps.creators.models import CreatorProfile, CreatorRole


class CreatorProfileSerializer(RejectUnknownFieldsMixin, serializers.ModelSerializer):
    displayName = serializers.CharField(source="display_name")
    isApproved = serializers.BooleanField(source="is_approved", read_only=True)

    class Meta:
        model = CreatorProfile
        fields = ("id", "displayName", "biography", "roles", "isApproved")

    def validate_roles(self, value):
        allowed = set(CreatorRole.values)
        if not isinstance(value, list) or not set(value) <= allowed:
            raise serializers.ValidationError("Contains an unsupported creator role.")
        return list(dict.fromkeys(value))


class CreatorTrackSerializer(CompactTrackSerializer):
    reviewStatus = serializers.CharField(source="review_status")
    processingStatus = serializers.CharField(source="processing_status")
    submittedAt = serializers.DateTimeField(source="submitted_at")
    reviewedAt = serializers.DateTimeField(source="reviewed_at")

    class Meta(CompactTrackSerializer.Meta):
        fields = CompactTrackSerializer.Meta.fields + (
            "reviewStatus",
            "processingStatus",
            "submittedAt",
            "reviewedAt",
        )


class DraftMetadataSerializer(RejectUnknownFieldsMixin, serializers.ModelSerializer):
    titleNe = serializers.CharField(source="title_ne", required=False)
    titleEn = serializers.CharField(source="title_en", required=False, allow_blank=True)
    descriptionNe = serializers.CharField(
        source="description_ne", required=False, allow_blank=True
    )
    descriptionEn = serializers.CharField(
        source="description_en", required=False, allow_blank=True
    )
    chapterNumber = serializers.IntegerField(
        source="chapter_number", required=False, allow_null=True, min_value=1
    )
    trackNumber = serializers.IntegerField(
        source="track_number", required=False, allow_null=True, min_value=1
    )
    isExplicit = serializers.BooleanField(source="is_explicit", required=False)
    copyrightStatus = serializers.ChoiceField(
        choices=CopyrightStatus.choices,
        required=False,
    )
    copyrightOwner = serializers.CharField(required=False, allow_blank=True)
    licenseNotes = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = AudioTrack
        fields = (
            "titleNe",
            "titleEn",
            "descriptionNe",
            "descriptionEn",
            "chapterNumber",
            "trackNumber",
            "isExplicit",
            "copyrightStatus",
            "copyrightOwner",
            "licenseNotes",
        )

    def validate(self, attrs):
        protected = {
            "isPublished",
            "publishedAt",
            "reviewStatus",
            "processingStatus",
            "isPremium",
            "audioMasterFile",
            "streamFileHigh",
            "streamFileLow",
        }.intersection(self.initial_data)
        if protected:
            raise serializers.ValidationError(
                {
                    field: "This field is managed by staff or the media workflow."
                    for field in sorted(protected)
                }
            )
        if self.instance.review_status not in (
            TrackReviewStatus.DRAFT,
            TrackReviewStatus.REJECTED,
        ):
            raise serializers.ValidationError(
                "Only draft or rejected tracks can be edited."
            )
        return attrs

    def update(self, instance, validated_data):
        rights = {
            key: validated_data.pop(key)
            for key in ("copyrightStatus", "copyrightOwner", "licenseNotes")
            if key in validated_data
        }
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        self.context["rights_changes"] = rights
        return instance


class ProcessingStatusSerializer(serializers.ModelSerializer):
    processingStatus = serializers.CharField(source="processing_status")
    reviewStatus = serializers.CharField(source="review_status")

    class Meta:
        model = AudioTrack
        fields = ("id", "slug", "processingStatus", "reviewStatus", "updated_at")


class CreatorAnalyticsSerializer(serializers.Serializer):
    playCount = serializers.IntegerField()
    favoriteCount = serializers.IntegerField()
    uniqueListeners = serializers.IntegerField()
    playbackSessions = serializers.IntegerField()
    completedSessions = serializers.IntegerField()
    listenedSeconds = serializers.DecimalField(max_digits=16, decimal_places=3)
