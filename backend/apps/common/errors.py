"""Stable API error envelopes and the global DRF exception handler."""

import logging

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger(__name__)


def error_response(
    *,
    detail: str,
    code: str,
    errors=None,
    status_code: int = status.HTTP_400_BAD_REQUEST,
) -> Response:
    payload = {"detail": detail, "code": code}
    if errors is not None:
        payload["errors"] = errors
    return Response(payload, status=status_code)


def api_exception_handler(exc, context):
    """Normalize expected and unexpected exceptions into one safe envelope."""

    if isinstance(exc, DjangoValidationError):
        exc = ValidationError(
            getattr(exc, "message_dict", None) or getattr(exc, "messages", None)
        )

    response = drf_exception_handler(exc, context)
    if response is None:
        logger.error(
            "Unhandled API exception",
            exc_info=(type(exc), exc, exc.__traceback__),
        )
        return error_response(
            detail="An unexpected error occurred.",
            code="server_error",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    if isinstance(exc, ValidationError):
        return error_response(
            detail="Validation failed.",
            code="validation_error",
            errors=response.data,
            status_code=response.status_code,
        )

    detail = _extract_detail(response.data)
    code = exc.get_codes() if isinstance(exc, APIException) else "api_error"
    if not isinstance(code, str):
        code = "api_error"

    return error_response(
        detail=detail,
        code=code,
        status_code=response.status_code,
    )


def _extract_detail(data) -> str:
    if isinstance(data, dict) and "detail" in data:
        return str(data["detail"])
    if isinstance(data, list):
        return " ".join(str(item) for item in data)
    return str(data)
