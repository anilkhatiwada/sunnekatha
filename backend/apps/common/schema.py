"""Reusable serializers and drf-spectacular response declarations."""

from drf_spectacular.utils import OpenApiExample, OpenApiResponse
from rest_framework import serializers


class ApiErrorSerializer(serializers.Serializer):
    detail = serializers.CharField(help_text="Safe, human-readable error summary.")
    code = serializers.CharField(help_text="Stable machine-readable error code.")
    errors = serializers.DictField(
        required=False,
        help_text="Field or non-field validation errors, when applicable.",
    )


ERROR_EXAMPLES = [
    OpenApiExample(
        "Validation error",
        value={
            "detail": "Validation failed.",
            "code": "validation_error",
            "errors": {
                "progressSeconds": ["Ensure this value is greater than or equal to 0."]
            },
        },
        response_only=True,
        status_codes=["400"],
    ),
    OpenApiExample(
        "Authentication required",
        value={
            "detail": "Authentication credentials were not provided.",
            "code": "not_authenticated",
        },
        response_only=True,
        status_codes=["401"],
    ),
    OpenApiExample(
        "Permission denied",
        value={
            "detail": "You do not have permission to perform this action.",
            "code": "permission_denied",
        },
        response_only=True,
        status_codes=["403"],
    ),
    OpenApiExample(
        "Request throttled",
        value={
            "detail": "Request was throttled. Expected available in 60 seconds.",
            "code": "throttled",
        },
        response_only=True,
        status_codes=["429"],
    ),
]


def error_schema_response(description: str) -> OpenApiResponse:
    return OpenApiResponse(
        response=ApiErrorSerializer,
        description=description,
        examples=ERROR_EXAMPLES,
    )


STANDARD_ERROR_RESPONSES = {
    400: error_schema_response("The request is invalid."),
    401: error_schema_response("Authentication is required or invalid."),
    403: error_schema_response("The action is not permitted."),
    404: error_schema_response("The resource does not exist."),
    429: error_schema_response("The request rate limit was exceeded."),
    500: error_schema_response("An unexpected server error occurred."),
}


def with_standard_errors(responses=None):
    """Merge endpoint-specific OpenAPI responses with the standard errors."""

    return {**STANDARD_ERROR_RESPONSES, **(responses or {})}
