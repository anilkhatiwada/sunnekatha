from types import SimpleNamespace

from rest_framework.test import APIRequestFactory, force_authenticate

from apps.common.permissions import IsAdminOrReadOnly, IsOwnerOrReadOnly


def request(method, user=None):
    result = getattr(APIRequestFactory(), method.lower())("/")
    if user is not None:
        force_authenticate(result, user=user)
        result.user = user
    return result


def test_admin_or_read_only_allows_public_read():
    assert IsAdminOrReadOnly().has_permission(request("GET"), None) is True


def test_admin_or_read_only_rejects_non_staff_write():
    user = SimpleNamespace(is_authenticated=True, is_active=True, is_staff=False)

    assert IsAdminOrReadOnly().has_permission(request("POST", user), None) is False


def test_owner_or_read_only_allows_owner_write():
    user = SimpleNamespace(is_authenticated=True, is_staff=False)
    obj = SimpleNamespace(owner=user)

    assert (
        IsOwnerOrReadOnly().has_object_permission(
            request("PATCH", user),
            SimpleNamespace(),
            obj,
        )
        is True
    )
