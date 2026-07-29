from django.db import transaction
from django.db.models import F, Q
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework.generics import GenericAPIView, ListAPIView
from rest_framework.response import Response

from apps.accounts.permissions import IsAuthenticatedAndActive
from apps.authors.models import Author
from apps.catalog.track_views import public_track_queryset
from apps.library.models import (
    FavoriteTrack,
    FollowedAuthor,
    FollowedNarrator,
    SavedPlaylist,
)
from apps.library.serializers import (
    AuthorRelationshipSerializer,
    FavoriteTrackSerializer,
    FollowedAuthorSerializer,
    FollowedNarratorSerializer,
    NarratorRelationshipSerializer,
    PlaylistRelationshipSerializer,
    SavedPlaylistSerializer,
    TrackRelationshipSerializer,
)
from apps.narrators.models import Narrator
from apps.playlists.models import Playlist, PlaylistVisibility
from apps.playlists.views import playlist_queryset


class LibraryListView(ListAPIView):
    permission_classes = [IsAuthenticatedAndActive]


class FavoriteTrackListView(LibraryListView):
    serializer_class = FavoriteTrackSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return public_track_queryset().none()
        return (
            public_track_queryset()
            .filter(favorited_by__user=self.request.user)
            .order_by("-favorited_by__created_at", "id")
        )


class SavedPlaylistListView(LibraryListView):
    serializer_class = SavedPlaylistSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return playlist_queryset(include_tracks=False).none()
        visible = (
            Q(is_published=True) & ~Q(visibility=PlaylistVisibility.PRIVATE)
        ) | Q(owner=self.request.user)
        return (
            playlist_queryset(include_tracks=False)
            .filter(saved_by__user=self.request.user)
            .filter(visible)
            .order_by("-saved_by__created_at", "id")
        )


class FollowedAuthorListView(LibraryListView):
    serializer_class = FollowedAuthorSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Author.objects.none()
        return Author.objects.filter(followers__user=self.request.user).order_by(
            "-followers__created_at",
            "id",
        )


class FollowedNarratorListView(LibraryListView):
    serializer_class = FollowedNarratorSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Narrator.objects.none()
        return (
            Narrator.objects.filter(followers__user=self.request.user)
            .select_related("user")
            .order_by("-followers__created_at", "id")
        )


class RelationshipView(GenericAPIView):
    permission_classes = [IsAuthenticatedAndActive]
    relationship_model = None
    target_model = None
    target_field = ""
    state_field = ""

    def get_target_queryset(self):
        return self.target_model.objects.all()

    def get_target(self, target_id):
        return get_object_or_404(self.get_target_queryset(), pk=target_id)

    def state_response(self, target, state):
        serializer = self.get_serializer(
            {"id": target.pk, self.state_field: state},
        )
        return Response(serializer.data)

    def relationship_added(self, target):
        del target

    def relationship_removed(self, target):
        del target

    @transaction.atomic
    def add(self, request, target_id):
        target = self.get_target(target_id)
        _, created = self.relationship_model.objects.get_or_create(
            user=request.user,
            **{self.target_field: target},
        )
        if created:
            self.relationship_added(target)
        return self.state_response(target, True)

    @transaction.atomic
    def remove(self, request, target_id):
        target = self.get_target(target_id)
        deleted, _ = self.relationship_model.objects.filter(
            user=request.user,
            **{self.target_field: target},
        ).delete()
        if deleted:
            self.relationship_removed(target)
        return self.state_response(target, False)

    post = add
    put = add
    delete = remove


class FavoriteTrackView(RelationshipView):
    serializer_class = TrackRelationshipSerializer
    relationship_model = FavoriteTrack
    target_field = "track"
    state_field = "is_favorited"

    def get_target_queryset(self):
        return public_track_queryset()


class SavePlaylistView(RelationshipView):
    serializer_class = PlaylistRelationshipSerializer
    relationship_model = SavedPlaylist
    target_model = Playlist
    target_field = "playlist"
    state_field = "is_playlist_saved"

    def get_target_queryset(self):
        visible = (
            Q(is_published=True) & ~Q(visibility=PlaylistVisibility.PRIVATE)
        ) | Q(owner=self.request.user)
        return Playlist.objects.filter(visible)


class FollowAuthorView(RelationshipView):
    serializer_class = AuthorRelationshipSerializer
    relationship_model = FollowedAuthor
    target_model = Author
    target_field = "author"
    state_field = "is_author_followed"


class FollowNarratorView(RelationshipView):
    serializer_class = NarratorRelationshipSerializer
    relationship_model = FollowedNarrator
    target_model = Narrator
    target_field = "narrator"
    state_field = "is_narrator_followed"

    def relationship_added(self, target):
        Narrator.objects.filter(pk=target.pk).update(
            follower_count_cache=F("follower_count_cache") + 1
        )

    def relationship_removed(self, target):
        Narrator.objects.filter(
            pk=target.pk,
            follower_count_cache__gt=0,
        ).update(follower_count_cache=F("follower_count_cache") - 1)


for view_class in (
    FavoriteTrackView,
    SavePlaylistView,
    FollowAuthorView,
    FollowNarratorView,
):
    view_class.post = extend_schema(
        request=None,
        responses=view_class.serializer_class,
    )(view_class.post)
    view_class.put = extend_schema(
        request=None,
        responses=view_class.serializer_class,
    )(view_class.put)
    view_class.delete = extend_schema(
        request=None,
        responses=view_class.serializer_class,
    )(view_class.delete)
