import csv
from dataclasses import dataclass, field
from io import StringIO

from django.contrib import messages
from django.contrib.admin import helpers
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import HttpResponse
from django.template.response import TemplateResponse


@dataclass(frozen=True)
class BulkActionFailure:
    object_id: str
    label: str
    reason: str


@dataclass
class BulkActionReport:
    succeeded: int = 0
    failures: list[BulkActionFailure] = field(default_factory=list)

    @property
    def failed(self):
        return len(self.failures)


def validation_message(exc):
    if isinstance(exc, ValidationError):
        return "; ".join(exc.messages)
    return str(exc) or "Permission denied."


def run_object_action(*, model_admin, request, queryset, operation):
    """Run a service operation per object and retain every failure reason."""
    report = BulkActionReport()
    for obj in queryset:
        if not model_admin.has_change_permission(request, obj):
            report.failures.append(
                BulkActionFailure(str(obj.pk), str(obj), "No permission for this item.")
            )
            continue
        try:
            operation(obj)
        except (PermissionDenied, ValidationError) as exc:
            report.failures.append(
                BulkActionFailure(str(obj.pk), str(obj), validation_message(exc))
            )
        else:
            report.succeeded += 1
    return report


def confirm_bulk_action(
    *,
    model_admin,
    request,
    queryset,
    action_name,
    title,
    warning,
    submit_label,
):
    return TemplateResponse(
        request,
        "admin/common/bulk_action_confirmation.html",
        {
            **model_admin.admin_site.each_context(request),
            "title": title,
            "warning": warning,
            "submit_label": submit_label,
            "queryset": queryset,
            "action_name": action_name,
            "action_checkbox_name": helpers.ACTION_CHECKBOX_NAME,
            "opts": model_admin.model._meta,
        },
    )


def report_bulk_action(model_admin, request, *, verb, report):
    if report.succeeded:
        model_admin.message_user(
            request,
            f"{verb} {report.succeeded} selected item(s).",
            messages.SUCCESS,
        )
    if report.failures:
        details = "; ".join(
            f"{failure.label}: {failure.reason}" for failure in report.failures[:10]
        )
        remainder = max(0, report.failed - 10)
        if remainder:
            details += f"; and {remainder} more failure(s)"
        model_admin.message_user(
            request,
            f"{report.failed} item(s) were not changed. {details}",
            messages.WARNING,
        )


def export_metadata_csv(*, queryset, fields, filename):
    """Export explicitly selected scalar metadata fields; never infer file fields."""

    def serialize(value):
        if value is None:
            return ""
        if hasattr(value, "isoformat"):
            return value.isoformat()
        return value

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(fields)
    for obj in queryset:
        writer.writerow([serialize(getattr(obj, field)) for field in fields])
    response = HttpResponse(output.getvalue(), content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
