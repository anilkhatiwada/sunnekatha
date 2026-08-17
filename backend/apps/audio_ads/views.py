from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audio_ads.models import AudioAdvertisement
from apps.audio_ads.serializers import (
    AudioAdvertisementEligibilityResponseSerializer,
    AudioAdvertisementEligibilitySerializer,
    AudioAdvertisementStartedResponseSerializer,
    AudioAdvertisementStartedSerializer,
)
from apps.audio_ads.services import audio_advertisement_service
from apps.catalog.models import AudioTrack
from apps.media_access.services import cloudfront_media_service


class NextAudioAdvertisementView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = "audio_ad_select"

    @extend_schema(
        request=AudioAdvertisementEligibilitySerializer,
        responses={200: AudioAdvertisementEligibilityResponseSerializer},
        tags=["audio advertisements"],
    )
    def post(self, request):
        serializer = AudioAdvertisementEligibilitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        selection = audio_advertisement_service.select_for_playback(
            session_id=serializer.validated_data["sessionId"],
            playback_sequence=serializer.validated_data["playbackSequence"],
        )
        advertisement = selection.advertisement
        payload = {
            "advertisement": (
                cloudfront_media_service.deliver_audio_advertisement(advertisement)
                if advertisement
                else None
            ),
            "reason": selection.reason,
        }
        return Response(AudioAdvertisementEligibilityResponseSerializer(payload).data)


class AudioAdvertisementStartedView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = "audio_ad_started"

    @extend_schema(
        request=AudioAdvertisementStartedSerializer,
        responses={200: AudioAdvertisementStartedResponseSerializer},
        tags=["audio advertisements"],
    )
    def post(self, request, advertisement_id):
        serializer = AudioAdvertisementStartedSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        advertisement = get_object_or_404(
            AudioAdvertisement,
            pk=advertisement_id,
        )
        track_id = serializer.validated_data.get("trackId")
        track = AudioTrack.objects.filter(pk=track_id).first() if track_id else None
        _, created = audio_advertisement_service.record_started(
            advertisement=advertisement,
            session_id=serializer.validated_data["sessionId"],
            playback_sequence=serializer.validated_data["playbackSequence"],
            source=serializer.validated_data["source"],
            track=track,
            user=request.user,
        )
        return Response({"counted": created})
