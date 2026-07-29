from decimal import Decimal

from django.db import transaction
from django.db.models import F, Max
from rest_framework.exceptions import ValidationError

from apps.library.models import UserQueue, UserQueueItem


def clamp_queue_index(index, length):
    if length == 0:
        return -1
    return min(max(int(index), 0), length - 1)


class UserQueueService:
    def get_or_create(self, user):
        queue, _ = UserQueue.objects.get_or_create(user=user)
        return queue

    @transaction.atomic
    def replace(self, *, queue, tracks, current_index=0, position_seconds=0):
        locked = UserQueue.objects.select_for_update().get(pk=queue.pk)
        UserQueueItem.objects.filter(queue=locked).delete()
        UserQueueItem.objects.bulk_create(
            [
                UserQueueItem(queue=locked, track=track, position=position)
                for position, track in enumerate(tracks, start=1)
            ]
        )
        locked.current_index = clamp_queue_index(current_index, len(tracks))
        locked.position_seconds = (
            Decimal(str(position_seconds))
            if locked.current_index >= 0
            else Decimal("0")
        )
        locked.save(update_fields=("current_index", "position_seconds", "updated_at"))
        return locked

    @transaction.atomic
    def add(self, *, queue, track):
        locked = UserQueue.objects.select_for_update().get(pk=queue.pk)
        last = (
            UserQueueItem.objects.filter(queue=locked).aggregate(Max("position"))[
                "position__max"
            ]
            or 0
        )
        item = UserQueueItem.objects.create(
            queue=locked,
            track=track,
            position=last + 1,
        )
        if locked.current_index < 0:
            locked.current_index = 0
            locked.position_seconds = 0
            locked.save(
                update_fields=("current_index", "position_seconds", "updated_at")
            )
        else:
            locked.save(update_fields=("updated_at",))
        return item

    @transaction.atomic
    def play_next(self, *, queue, track):
        locked = UserQueue.objects.select_for_update().get(pk=queue.pk)
        items = list(
            UserQueueItem.objects.select_for_update()
            .filter(queue=locked)
            .order_by("position")
        )
        insertion_index = max(locked.current_index + 1, 0)
        new_item = UserQueueItem(queue=locked, track=track, position=0)
        items.insert(insertion_index, new_item)
        self._replace_item_positions(locked, items)
        if locked.current_index < 0:
            locked.current_index = 0
            locked.position_seconds = 0
            locked.save(
                update_fields=("current_index", "position_seconds", "updated_at")
            )
        else:
            locked.save(update_fields=("updated_at",))
        return new_item

    @transaction.atomic
    def remove(self, *, queue, item_id):
        locked = UserQueue.objects.select_for_update().get(pk=queue.pk)
        items = list(
            UserQueueItem.objects.select_for_update()
            .filter(queue=locked)
            .order_by("position")
        )
        current_item_id = (
            items[locked.current_index].id
            if 0 <= locked.current_index < len(items)
            else None
        )
        removed_index = next(
            (index for index, item in enumerate(items) if item.id == item_id),
            None,
        )
        if removed_index is None:
            raise ValidationError({"itemId": "Queue item was not found."})
        removed_current = items[removed_index].id == current_item_id
        items.pop(removed_index).delete()
        self._replace_item_positions(locked, items)
        if not items:
            locked.current_index = -1
            locked.position_seconds = 0
        elif removed_current:
            locked.current_index = min(removed_index, len(items) - 1)
            locked.position_seconds = 0
        else:
            locked.current_index = next(
                (
                    index
                    for index, item in enumerate(items)
                    if item.id == current_item_id
                ),
                clamp_queue_index(locked.current_index, len(items)),
            )
        locked.save(update_fields=("current_index", "position_seconds", "updated_at"))

    @transaction.atomic
    def reorder(self, *, queue, item_ids):
        locked = UserQueue.objects.select_for_update().get(pk=queue.pk)
        items = list(
            UserQueueItem.objects.select_for_update()
            .filter(queue=locked)
            .order_by("position")
        )
        existing_ids = [item.id for item in items]
        if len(item_ids) != len(set(item_ids)):
            raise ValidationError({"itemIds": "Queue item IDs must be unique."})
        if len(item_ids) != len(existing_ids) or set(item_ids) != set(existing_ids):
            raise ValidationError(
                {"itemIds": "Provide every current queue item exactly once."}
            )
        current_item_id = (
            existing_ids[locked.current_index]
            if 0 <= locked.current_index < len(existing_ids)
            else None
        )
        by_id = {item.id: item for item in items}
        ordered = [by_id[item_id] for item_id in item_ids]
        self._replace_item_positions(locked, ordered)
        locked.current_index = (
            item_ids.index(current_item_id) if current_item_id else -1
        )
        locked.save(update_fields=("current_index", "updated_at"))
        return locked

    @transaction.atomic
    def clear(self, *, queue):
        locked = UserQueue.objects.select_for_update().get(pk=queue.pk)
        UserQueueItem.objects.filter(queue=locked).delete()
        locked.current_index = -1
        locked.position_seconds = 0
        locked.save(update_fields=("current_index", "position_seconds", "updated_at"))
        return locked

    @transaction.atomic
    def update_position(self, *, queue, current_index, position_seconds):
        locked = UserQueue.objects.select_for_update().get(pk=queue.pk)
        item_count = UserQueueItem.objects.filter(queue=locked).count()
        locked.current_index = clamp_queue_index(current_index, item_count)
        locked.position_seconds = (
            Decimal(str(position_seconds))
            if locked.current_index >= 0
            else Decimal("0")
        )
        locked.save(update_fields=("current_index", "position_seconds", "updated_at"))
        return locked

    @staticmethod
    def _replace_item_positions(queue, items):
        existing_count = UserQueueItem.objects.filter(queue=queue).count()
        if existing_count:
            UserQueueItem.objects.filter(queue=queue).update(
                position=F("position") + existing_count + len(items) + 1
            )
        for position, item in enumerate(items, start=1):
            if not item._state.adding:
                item.position = position
                item.save(update_fields=("position", "updated_at"))
            else:
                item.position = position
                item.save()


user_queue_service = UserQueueService()
