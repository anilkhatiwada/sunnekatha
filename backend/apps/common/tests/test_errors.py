from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError

from apps.common.errors import api_exception_handler, error_response


def test_error_response_uses_standard_envelope():
    response = error_response(
        detail="Invalid input.",
        code="invalid",
        errors={"field": ["Required."]},
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data == {
        "detail": "Invalid input.",
        "code": "invalid",
        "errors": {"field": ["Required."]},
    }


def test_validation_error_is_normalized():
    response = api_exception_handler(
        ValidationError({"title": ["This field is required."]}),
        {},
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["code"] == "validation_error"
    assert response.data["errors"] == {"title": ["This field is required."]}


def test_django_validation_error_is_normalized():
    response = api_exception_handler(
        DjangoValidationError({"slug": ["Invalid slug."]}),
        {},
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["code"] == "validation_error"
    assert "slug" in response.data["errors"]


def test_not_found_error_preserves_stable_code():
    response = api_exception_handler(NotFound("Missing."), {})

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.data == {"detail": "Missing.", "code": "not_found"}


def test_unhandled_error_hides_internal_detail(caplog):
    response = api_exception_handler(RuntimeError("sensitive detail"), {})

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.data == {
        "detail": "An unexpected error occurred.",
        "code": "server_error",
    }
    assert "sensitive detail" not in str(response.data)
