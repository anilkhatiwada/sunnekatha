from django.db.models import Q
from rest_framework.permissions import BasePermission


class IsCreatorOrStaff(BasePermission):
    def has_permission(self, request, view):
        del view
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.is_active
            and (user.is_creator or user.is_staff)
        )


def owned_tracks(user):
    from apps.catalog.models import AudioTrack

    if user.is_staff:
        return AudioTrack.objects.all()
    return AudioTrack.objects.filter(
        Q(narrator__user=user) | Q(contributors__creator__user=user)
    ).distinct()


def can_manage_draft(user, track):
    return bool(
        not track.is_published
        and (user.is_staff or owned_tracks(user).filter(pk=track.pk).exists())
    )


def can_manage_rights(user, track):
    return bool(
        user.is_staff
        or track.contributors.filter(
            creator__user=user,
            role="rights_holder",
        ).exists()
    )
