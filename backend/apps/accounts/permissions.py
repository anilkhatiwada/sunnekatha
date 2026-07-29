from rest_framework.permissions import BasePermission


class IsAuthenticatedAndActive(BasePermission):
    message = "An active account is required."

    def has_permission(self, request, view):
        del view
        return bool(
            request.user and request.user.is_authenticated and request.user.is_active
        )
