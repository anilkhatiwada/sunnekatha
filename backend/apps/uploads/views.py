from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from apps.common.schema import with_standard_errors
from apps.uploads.models import UploadSession
from apps.uploads.permissions import IsCreatorOrStaff
from apps.uploads.serializers import (
    UploadRequestSerializer,
    UploadSessionSerializer,
    UploadURLSerializer,
)
from apps.uploads.services import upload_session_service


class UploadSessionMixin:
    permission_classes = [IsCreatorOrStaff]
    queryset = UploadSession.objects.all()
    throttle_scope = "upload"

    def get_session(self):
        return get_object_or_404(
            UploadSession.objects.filter(user=self.request.user),
            pk=self.kwargs["session_id"],
        )


class RequestUploadView(UploadSessionMixin, GenericAPIView):
    serializer_class = UploadRequestSerializer

    @extend_schema(
        summary="Request a direct upload",
        description=(
            "Creates an expiring, server-controlled object key and returns a "
            "presigned S3 POST. Send every returned `upload.fields` value plus "
            "the file directly to `upload.url`; never upload file bytes to Django."
        ),
        request=UploadRequestSerializer,
        responses=with_standard_errors({status.HTTP_201_CREATED: UploadURLSerializer}),
        examples=[
            OpenApiExample(
                "Audio master request",
                value={
                    "uploadType": "audio_master",
                    "originalFilename": "katha.mp3",
                    "contentType": "audio/mpeg",
                    "expectedSize": 8451200,
                },
                request_only=True,
            ),
            OpenApiExample(
                "Presigned POST response",
                value={
                    "id": "6f37bcd4-412d-44b6-b335-9c2c2d506a19",
                    "uploadType": "audio_master",
                    "objectKey": (
                        "temporary/uploads/audio-master/user/session/object.mp3"
                    ),
                    "originalFilename": "katha.mp3",
                    "contentType": "audio/mpeg",
                    "expectedSize": 8451200,
                    "status": "pending",
                    "expiresAt": "2026-07-23T17:15:00Z",
                    "createdAt": "2026-07-23T17:00:00Z",
                    "updatedAt": "2026-07-23T17:00:00Z",
                    "upload": {
                        "url": "https://private-bucket.s3.amazonaws.com/",
                        "fields": {"key": "temporary/uploads/audio-master/..."},
                    },
                },
                response_only=True,
                status_codes=["201"],
            ),
        ],
        tags=["uploads"],
    )
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        session, upload = upload_session_service.request(
            user=request.user,
            size=serializer.validated_data.pop("expected_size"),
            **serializer.validated_data,
        )
        payload = {
            **UploadSessionSerializer(session).data,
            "upload": upload,
        }
        return Response(payload, status=status.HTTP_201_CREATED)


class UploadStatusView(UploadSessionMixin, GenericAPIView):
    serializer_class = UploadSessionSerializer

    @extend_schema(
        summary="Check an upload session",
        description=(
            "Returns the caller-owned upload session and refreshes expiry state."
        ),
        responses=with_standard_errors({200: UploadSessionSerializer}),
        tags=["uploads"],
    )
    def get(self, request, session_id):
        del request, session_id
        session = upload_session_service.refresh_status(
            self.get_session(),
            actor=self.request.user,
        )
        return Response(self.get_serializer(session).data)


class ConfirmUploadView(UploadSessionMixin, GenericAPIView):
    serializer_class = UploadSessionSerializer

    @extend_schema(
        summary="Confirm a direct upload",
        description=(
            "Verifies that the expected object exists with the signed size and "
            "content metadata before marking the session confirmed."
        ),
        request=None,
        responses=with_standard_errors({200: UploadSessionSerializer}),
        tags=["uploads"],
    )
    def post(self, request, session_id):
        del request, session_id
        session = upload_session_service.confirm(
            session=self.get_session(),
            actor=self.request.user,
        )
        return Response(self.get_serializer(session).data)


class CancelUploadView(UploadSessionMixin, GenericAPIView):
    serializer_class = UploadSessionSerializer

    @extend_schema(
        summary="Cancel an upload session",
        request=None,
        responses=with_standard_errors({200: UploadSessionSerializer}),
        tags=["uploads"],
    )
    def post(self, request, session_id):
        del request, session_id
        session = upload_session_service.cancel(
            session=self.get_session(),
            actor=self.request.user,
        )
        return Response(self.get_serializer(session).data)
