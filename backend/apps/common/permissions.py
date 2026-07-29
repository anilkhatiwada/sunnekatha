from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsAdminOrReadOnly(BasePermission):
    """Allow public reads while limiting writes to active staff users."""

    def has_permission(self, request, view):
        del view
        return request.method in SAFE_METHODS or bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_active
            and request.user.is_staff
        )


class IsOwnerOrReadOnly(BasePermission):
    """Allow public reads and owner/staff writes."""

    owner_field = "owner"

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_staff:
            return True

        owner_field = getattr(view, "owner_field", self.owner_field)
        return getattr(obj, owner_field, None) == request.user


class IsSelfOrAdmin(BasePermission):
    """Limit an object to its represented user or an active staff user."""

    def has_object_permission(self, request, view, obj):
        del view
        if not request.user or not request.user.is_authenticated:
            return False
        return bool(request.user.is_staff or obj == request.user)
