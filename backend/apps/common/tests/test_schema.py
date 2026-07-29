from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient


def test_openapi_schema_is_available():
    response = APIClient().get(reverse("schema"), HTTP_ACCEPT="application/json")

    assert response.status_code == status.HTTP_200_OK
    schema = response.json()
    assert schema["info"]["title"] == "SunneKatha API"
    assert schema["components"]["securitySchemes"]["jwtAuth"] == {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
    }


def test_openapi_documents_critical_frontend_flows():
    schema = (
        APIClient()
        .get(
            reverse("schema"),
            HTTP_ACCEPT="application/json",
        )
        .json()
    )
    paths = schema["paths"]

    upload = paths["/api/v1/uploads/"]["post"]
    stream = paths["/api/v1/tracks/{slug}/stream/"]["get"]
    progress = paths["/api/v1/me/listening-progress/{track_id}/"]["put"]
    queue = paths["/api/v1/me/queue/"]["put"]

    assert upload["summary"] == "Request a direct upload"
    assert (
        "AudioMasterRequest"
        in upload["requestBody"]["content"]["application/json"]["examples"]
    )
    assert "premium" in stream["description"].lower()
    assert progress["summary"] == "Replace listening progress"
    assert queue["summary"] == "Replace the synchronized queue"
    assert "ApiError" in schema["components"]["schemas"]
