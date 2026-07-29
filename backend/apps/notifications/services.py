from django.contrib.auth import get_user_model

from apps.notifications.models import Notification, NotificationType

User = get_user_model()


class NotificationService:
    def create_for_users(
        self,
        *,
        user_ids,
        notification_type,
        title,
        message="",
        data=None,
        action_url="",
        deduplication_key="",
    ):
        recipients = set(user_ids)
        if not recipients:
            return 0
        notifications = [
            Notification(
                recipient_id=user_id,
                notification_type=notification_type,
                title=title,
                message=message,
                data=data or {},
                action_url=action_url,
                deduplication_key=deduplication_key,
            )
            for user_id in recipients
        ]
        created = Notification.objects.bulk_create(
            notifications,
            ignore_conflicts=bool(deduplication_key),
        )
        return len(created)

    def track_published(self, track, *, include_creator_approval=False):
        from apps.library.models import FollowedAuthor, FollowedNarrator

        payload = {
            "trackId": str(track.id),
            "trackSlug": track.slug,
            "title": track.title_ne,
        }
        action_url = f"/track/{track.slug}"
        author_followers = FollowedAuthor.objects.filter(
            author_id=track.work.author_id
        ).values_list("user_id", flat=True)
        self.create_for_users(
            user_ids=author_followers,
            notification_type=NotificationType.FOLLOWED_AUTHOR_PUBLISHED,
            title=f"{track.work.author.name_ne}को नयाँ रचना",
            message=track.title_ne,
            data=payload,
            action_url=action_url,
            deduplication_key=f"author-published:{track.id}",
        )
        narrator_followers = FollowedNarrator.objects.filter(
            narrator_id=track.narrator_id
        ).values_list("user_id", flat=True)
        self.create_for_users(
            user_ids=narrator_followers,
            notification_type=NotificationType.FOLLOWED_NARRATOR_PUBLISHED,
            title=f"{track.narrator.name_ne}को नयाँ वाचन",
            message=track.title_ne,
            data=payload,
            action_url=action_url,
            deduplication_key=f"narrator-published:{track.id}",
        )
        if include_creator_approval:
            self.creator_submission_approved(track)

    def playlist_updated(self, playlist):
        from apps.library.models import SavedPlaylist

        recipients = SavedPlaylist.objects.filter(playlist=playlist).values_list(
            "user_id",
            flat=True,
        )
        return self.create_for_users(
            user_ids=recipients,
            notification_type=NotificationType.PLAYLIST_UPDATED,
            title="सेभ गरिएको प्लेलिस्ट अपडेट भयो",
            message=playlist.title_ne,
            data={"playlistId": str(playlist.id), "playlistSlug": playlist.slug},
            action_url=f"/playlist/{playlist.slug}",
        )

    def upload_processing_completed(self, upload_session, *, track=None):
        data = {
            "uploadSessionId": str(upload_session.id),
            "uploadType": upload_session.upload_type,
        }
        if track:
            data.update({"trackId": str(track.id), "trackSlug": track.slug})
        return self.create_for_users(
            user_ids=[upload_session.user_id],
            notification_type=NotificationType.UPLOAD_PROCESSING_COMPLETED,
            title="अपलोड प्रशोधन पूरा भयो",
            message=upload_session.original_filename,
            data=data,
            deduplication_key=f"upload-completed:{upload_session.id}",
        )

    def upload_processing_failed(self, upload_session):
        return self.create_for_users(
            user_ids=[upload_session.user_id],
            notification_type=NotificationType.UPLOAD_PROCESSING_FAILED,
            title="अपलोड प्रशोधन असफल भयो",
            message=upload_session.original_filename,
            data={
                "uploadSessionId": str(upload_session.id),
                "uploadType": upload_session.upload_type,
            },
            deduplication_key=f"upload-failed:{upload_session.id}",
        )

    def creator_submission_approved(self, track):
        return self._creator_submission(track, approved=True)

    def creator_submission_rejected(self, track):
        return self._creator_submission(track, approved=False)

    def creator_submission_reviewed(self, track, *, status, comment):
        recipients = set(track.contributors.values_list("creator__user_id", flat=True))
        if track.narrator.user_id:
            recipients.add(track.narrator.user_id)
        changes_requested = status == "changes_requested"
        state = "changes-requested" if changes_requested else "rejected"
        return self.create_for_users(
            user_ids=recipients,
            notification_type=(
                NotificationType.CREATOR_CHANGES_REQUESTED
                if changes_requested
                else NotificationType.CREATOR_SUBMISSION_REJECTED
            ),
            title=(
                "तपाईंको रचनामा परिवर्तन आवश्यक छ"
                if changes_requested
                else "तपाईंको रचना अस्वीकृत भयो"
            ),
            message=comment,
            data={
                "trackId": str(track.id),
                "trackSlug": track.slug,
                "reviewStatus": status,
            },
            action_url=f"/track/{track.slug}",
            deduplication_key=f"creator-{state}:{track.id}:{track.reviewed_at}",
        )

    def _creator_submission(self, track, *, approved):
        recipients = set(track.contributors.values_list("creator__user_id", flat=True))
        if track.narrator.user_id:
            recipients.add(track.narrator.user_id)
        notification_type = (
            NotificationType.CREATOR_SUBMISSION_APPROVED
            if approved
            else NotificationType.CREATOR_SUBMISSION_REJECTED
        )
        state = "approved" if approved else "rejected"
        return self.create_for_users(
            user_ids=recipients,
            notification_type=notification_type,
            title=("तपाईंको रचना स्वीकृत भयो" if approved else "तपाईंको रचना अस्वीकृत भयो"),
            message=track.title_ne,
            data={"trackId": str(track.id), "trackSlug": track.slug},
            action_url=f"/track/{track.slug}",
            deduplication_key=f"creator-{state}:{track.id}",
        )


notification_service = NotificationService()
