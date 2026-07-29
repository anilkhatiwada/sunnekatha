from rest_framework import serializers

from apps.common.serializers import RejectUnknownFieldsMixin
from apps.uploads.models import UploadSession, UploadType


class UploadRequestSerializer(RejectUnknownFieldsMixin, serializers.Serializer):
    uploadType = serializers.ChoiceField(
        source="upload_type",
        choices=UploadType.choices,
    )
    originalFilename = serializers.CharField(
        source="original_filename",
        max_length=255,
    )
    contentType = serializers.CharField(source="content_type", max_length=100)
    expectedSize = serializers.IntegerField(source="expected_size", min_value=1)


class UploadSessionSerializer(serializers.ModelSerializer):
    uploadType = serializers.CharField(source="upload_type")
    objectKey = serializers.CharField(source="object_key")
    originalFilename = serializers.CharField(source="original_filename")
    contentType = serializers.CharField(source="content_type")
    expectedSize = serializers.IntegerField(source="expected_size")
    expiresAt = serializers.DateTimeField(source="expires_at")
    createdAt = serializers.DateTimeField(source="created_at")
    updatedAt = serializers.DateTimeField(source="updated_at")

    class Meta:
        model = UploadSession
        fields = (
            "id",
            "uploadType",
            "objectKey",
            "originalFilename",
            "contentType",
            "expectedSize",
            "status",
            "expiresAt",
            "createdAt",
            "updatedAt",
        )
        read_only_fields = fields


class UploadURLSerializer(UploadSessionSerializer):
    upload = serializers.JSONField()

    class Meta(UploadSessionSerializer.Meta):
        fields = UploadSessionSerializer.Meta.fields + ("upload",)
