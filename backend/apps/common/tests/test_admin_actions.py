from types import SimpleNamespace

from django.core.exceptions import PermissionDenied, ValidationError

from apps.common.admin_actions import run_object_action


class FakeAdmin:
    def has_change_permission(self, request, obj):
        return obj.pk != 2


def test_run_object_action_reports_permission_and_validation_failures():
    objects = [
        SimpleNamespace(pk=1, __str__=lambda self: "Ready"),
        SimpleNamespace(pk=2, __str__=lambda self: "Forbidden"),
        SimpleNamespace(pk=3, __str__=lambda self: "Invalid"),
    ]

    def operation(obj):
        if obj.pk == 3:
            raise ValidationError("Not ready.")

    report = run_object_action(
        model_admin=FakeAdmin(),
        request=SimpleNamespace(),
        queryset=objects,
        operation=operation,
    )

    assert report.succeeded == 1
    assert report.failed == 2
    assert [failure.reason for failure in report.failures] == [
        "No permission for this item.",
        "Not ready.",
    ]


def test_run_object_action_reports_service_permission_failure():
    obj = SimpleNamespace(pk=1)

    def operation(_obj):
        raise PermissionDenied("Publisher role required.")

    report = run_object_action(
        model_admin=FakeAdmin(),
        request=SimpleNamespace(),
        queryset=[obj],
        operation=operation,
    )

    assert report.succeeded == 0
    assert report.failures[0].reason == "Publisher role required."
