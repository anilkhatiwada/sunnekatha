from rest_framework.permissions import BasePermission


class IsActiveStaff(BasePermission):
    message = "Active staff access is required."

    def has_permission(self, request, view):
        del view
        user = request.user
        return bool(user and user.is_authenticated and user.is_active and user.is_staff)
