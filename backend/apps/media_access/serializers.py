from rest_framework import serializers

from apps.catalog.track_serializers import CompactTrackSerializer


class StreamQuerySerializer(serializers.Serializer):
    quality = serializers.ChoiceField(
        choices=("low", "high", "auto"),
        default="auto",
        required=False,
    )
    includeIntroduction = serializers.BooleanField(default=False, required=False)


class StreamIntroductionSerializer(serializers.Serializer):
    url = serializers.URLField()
    expiresAt = serializers.DateTimeField(allow_null=True)
    duration = serializers.IntegerField(min_value=0)


class StreamAuthorizationSerializer(serializers.Serializer):
    status = serializers.CharField()
    accessType = serializers.CharField()
    isEntitled = serializers.BooleanField()
    isPrivileged = serializers.BooleanField()


class StreamResponseSerializer(serializers.Serializer):
    quality = serializers.ChoiceField(choices=("low", "high"))
    url = serializers.URLField()
    expiresAt = serializers.DateTimeField(allow_null=True)
    track = CompactTrackSerializer()
    authorization = StreamAuthorizationSerializer()
    introduction = StreamIntroductionSerializer(allow_null=True)
