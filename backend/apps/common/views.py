from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.db.utils import DatabaseError
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.schema import error_schema_response


class PublicSystemView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = []


class HealthCheckView(PublicSystemView):
    @extend_schema(
        tags=["System"],
        summary="Check API liveness",
        responses={
            200: inline_serializer(
                name="HealthResponse",
                fields={"status": serializers.CharField()},
            )
        },
    )
    def get(self, request):
        del request
        return Response({"status": "ok"})


class ReadinessCheckView(PublicSystemView):
    @extend_schema(
        tags=["System"],
        summary="Check API dependency readiness",
        responses={
            200: inline_serializer(
                name="ReadinessResponse",
                fields={
                    "status": serializers.CharField(),
                    "checks": serializers.DictField(child=serializers.CharField()),
                },
            ),
            503: error_schema_response("A required dependency is unavailable."),
        },
    )
    def get(self, request):
        del request

        checks = {}
        errors = {}
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
        except DatabaseError:
            errors["database"] = ["Database connection failed."]
        else:
            checks["database"] = "ok"

        cache_key = "system:readiness"
        try:
            cache.set(cache_key, "ok", timeout=5)
            if cache.get(cache_key) != "ok":
                raise RuntimeError("Cache write was not readable.")
            cache.delete(cache_key)
        except Exception:
            errors["cache"] = ["Cache connection failed."]
        else:
            checks["cache"] = "ok"

        if errors:
            return Response(
                {
                    "detail": "A required dependency is unavailable.",
                    "code": "service_unavailable",
                    "errors": errors,
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response({"status": "ready", "checks": checks})


class ApplicationVersionView(PublicSystemView):
    @extend_schema(
        tags=["System"],
        summary="Get the deployed application version",
        responses={
            200: inline_serializer(
                name="VersionResponse",
                fields={"version": serializers.CharField()},
            )
        },
    )
    def get(self, request):
        del request
        return Response({"version": settings.APP_VERSION})
