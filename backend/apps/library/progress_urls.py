from django.urls import path

from apps.library.playback_views import (
    EndPlaybackSessionView,
    ListeningHistoryListView,
    PlaybackSessionView,
    RecentlyPlayedListView,
    StartPlaybackSessionView,
)
from apps.library.progress_views import (
    ContinueListeningView,
    ListeningProgressDetailView,
    MarkListeningCompletedView,
    RemoveContinueListeningView,
)
from apps.library.queue_views import (
    AddQueueTrackView,
    CurrentQueueView,
    PlayNextView,
    QueuePositionView,
    QueueRepeatView,
    QueueShuffleView,
    RemoveQueueItemView,
    ReorderQueueView,
)

app_name = "listening_progress"

urlpatterns = [
    path("queue/", CurrentQueueView.as_view(), name="queue"),
    path("queue/items/", AddQueueTrackView.as_view(), name="queue-add"),
    path("queue/play-next/", PlayNextView.as_view(), name="queue-play-next"),
    path(
        "queue/items/<uuid:item_id>/",
        RemoveQueueItemView.as_view(),
        name="queue-remove",
    ),
    path("queue/reorder/", ReorderQueueView.as_view(), name="queue-reorder"),
    path("queue/position/", QueuePositionView.as_view(), name="queue-position"),
    path("queue/shuffle/", QueueShuffleView.as_view(), name="queue-shuffle"),
    path("queue/repeat/", QueueRepeatView.as_view(), name="queue-repeat"),
    path(
        "playback-sessions/",
        StartPlaybackSessionView.as_view(),
        name="session-start",
    ),
    path(
        "playback-sessions/<uuid:session_id>/",
        PlaybackSessionView.as_view(),
        name="session-update",
    ),
    path(
        "playback-sessions/<uuid:session_id>/end/",
        EndPlaybackSessionView.as_view(),
        name="session-end",
    ),
    path(
        "recently-played/",
        RecentlyPlayedListView.as_view(),
        name="recently-played",
    ),
    path(
        "listening-history/",
        ListeningHistoryListView.as_view(),
        name="history",
    ),
    path(
        "listening-progress/<uuid:track_id>/",
        ListeningProgressDetailView.as_view(),
        name="detail",
    ),
    path(
        "listening-progress/<uuid:track_id>/complete/",
        MarkListeningCompletedView.as_view(),
        name="complete",
    ),
    path(
        "listening-progress/<uuid:track_id>/remove/",
        RemoveContinueListeningView.as_view(),
        name="remove",
    ),
    path(
        "continue-listening/",
        ContinueListeningView.as_view(),
        name="continue-listening",
    ),
]
