from rest_framework import serializers

PLAYBACK_SOURCES = (
    "manual",
    "playlist",
    "queue",
    "play_all",
    "autoplay",
    "continue",
)


class AudioAdvertisementEligibilitySerializer(serializers.Serializer):
    sessionId = serializers.UUIDField()
    playbackSequence = serializers.IntegerField(min_value=1)
    trackId = serializers.UUIDField(required=False, allow_null=True)
    source = serializers.ChoiceField(choices=PLAYBACK_SOURCES)


class AudioAdvertisementStartedSerializer(AudioAdvertisementEligibilitySerializer):
    pass


class AudioAdvertisementDeliverySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    title = serializers.CharField()
    url = serializers.URLField()
    duration = serializers.IntegerField(min_value=0)
    expiresAt = serializers.DateTimeField(allow_null=True)


class AudioAdvertisementEligibilityResponseSerializer(serializers.Serializer):
    advertisement = AudioAdvertisementDeliverySerializer(allow_null=True)
    reason = serializers.CharField()


class AudioAdvertisementStartedResponseSerializer(serializers.Serializer):
    counted = serializers.BooleanField()
