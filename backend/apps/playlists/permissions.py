from rest_framework.permissions import BasePermission

from apps.playlists.models import PlaylistType


class CanManagePlaylist(BasePermission):
    message = "You do not have permission to modify this playlist."

    def has_object_permission(self, request, view, obj):
        del view
        user = request.user
        if not user or not user.is_authenticated or not user.is_active:
            return False
        if user.is_staff and obj.playlist_type != PlaylistType.USER:
            return True
        return obj.playlist_type == PlaylistType.USER and obj.owner_id == user.id
