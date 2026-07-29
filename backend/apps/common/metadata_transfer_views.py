from django import forms
from django.contrib import admin, messages
from django.core import signing
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse

from apps.common.audit import administrative_audit_service
from apps.common.metadata_transfer import (
    EXPORT_FIELDS,
    IMPORT_FIELDS,
    MAX_IMPORT_BYTES,
    MODEL_BY_EXPORT,
    MODEL_BY_IMPORT,
    ImportPreview,
    commit_import,
    export_csv,
    preview_import,
)
from apps.common.models import AdministrativeAuditAction

PREVIEW_SALT = "sunnekatha.metadata-import-preview"
PREVIEW_MAX_AGE = 30 * 60


class MetadataImportForm(forms.Form):
    import_type = forms.ChoiceField(
        choices=[(key, key.replace("_", " ").title()) for key in IMPORT_FIELDS]
    )
    csv_file = forms.FileField(help_text="UTF-8 CSV, maximum 1 MiB and 500 rows.")
    dry_run = forms.BooleanField(
        required=False,
        help_text="Validate and preview without allowing a database commit.",
    )

    def clean_csv_file(self):
        upload = self.cleaned_data["csv_file"]
        if upload.size > MAX_IMPORT_BYTES:
            raise forms.ValidationError("CSV cannot exceed 1 MiB.")
        if not upload.name.lower().endswith(".csv"):
            raise forms.ValidationError("Only .csv files are accepted.")
        return upload


def _model_permission(user, action, model):
    return user.has_perm(f"{model._meta.app_label}.{action}_{model._meta.model_name}")


def _require_workspace_access(user):
    if not user.has_perm("common.import_metadata") and not user.has_perm(
        "common.export_metadata"
    ):
        raise PermissionDenied


def metadata_transfer_view(request):
    _require_workspace_access(request.user)
    context = {
        **admin.site.each_context(request),
        "title": "Metadata import and export",
        "import_form": MetadataImportForm(),
        "export_types": EXPORT_FIELDS,
        "can_import": request.user.has_perm("common.import_metadata"),
        "can_export": request.user.has_perm("common.export_metadata"),
    }
    return render(request, "admin/common/metadata_transfer.html", context)


def metadata_export_view(request, kind):
    model = MODEL_BY_EXPORT.get(kind)
    if (
        model is None
        or not request.user.has_perm("common.export_metadata")
        or not _model_permission(request.user, "view", model)
    ):
        raise PermissionDenied
    content, count = export_csv(kind)
    administrative_audit_service.record_bulk(
        actor=request.user,
        action=AdministrativeAuditAction.METADATA_EXPORTED,
        object_type=f"{model._meta.app_label}.{model._meta.model_name}",
        object_count=count,
        reason=f"Authorized {kind} CSV export.",
    )
    response = HttpResponse(content, content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{kind}.csv"'
    return response


def metadata_import_preview_view(request):
    if request.method != "POST" or not request.user.has_perm("common.import_metadata"):
        raise PermissionDenied
    form = MetadataImportForm(request.POST, request.FILES)
    if not form.is_valid():
        context = {
            **admin.site.each_context(request),
            "title": "Metadata import and export",
            "import_form": form,
            "export_types": EXPORT_FIELDS,
            "can_import": True,
            "can_export": request.user.has_perm("common.export_metadata"),
        }
        return render(request, "admin/common/metadata_transfer.html", context)
    kind = form.cleaned_data["import_type"]
    model = MODEL_BY_IMPORT[kind]
    if not _model_permission(request.user, "add", model):
        raise PermissionDenied
    try:
        preview = preview_import(kind, form.cleaned_data["csv_file"].read())
    except ValidationError as exc:
        form.add_error("csv_file", exc)
        context = {
            **admin.site.each_context(request),
            "title": "Metadata import and export",
            "import_form": form,
            "export_types": EXPORT_FIELDS,
            "can_import": True,
            "can_export": request.user.has_perm("common.export_metadata"),
        }
        return render(request, "admin/common/metadata_transfer.html", context)
    token = (
        signing.dumps(
            {"kind": kind, "rows": list(preview.rows)},
            salt=PREVIEW_SALT,
            compress=True,
        )
        if preview.is_valid and not form.cleaned_data["dry_run"]
        else ""
    )
    return render(
        request,
        "admin/common/metadata_import_preview.html",
        {
            **admin.site.each_context(request),
            "title": "Preview metadata import",
            "preview": preview,
            "token": token,
            "dry_run": form.cleaned_data["dry_run"],
        },
    )


def metadata_import_confirm_view(request):
    if request.method != "POST" or not request.user.has_perm("common.import_metadata"):
        raise PermissionDenied
    try:
        payload = signing.loads(
            request.POST.get("preview_token", ""),
            salt=PREVIEW_SALT,
            max_age=PREVIEW_MAX_AGE,
        )
        kind = payload["kind"]
        model = MODEL_BY_IMPORT[kind]
    except (signing.BadSignature, KeyError):
        messages.error(request, "Import preview expired or was invalid.")
        return HttpResponseRedirect(reverse("admin_metadata_transfer"))
    if not _model_permission(request.user, "add", model):
        raise PermissionDenied
    preview = ImportPreview(kind, tuple(payload["rows"]), ())
    try:
        created = commit_import(preview, actor=request.user)
    except ValidationError as exc:
        messages.error(
            request,
            "Nothing was imported. Data changed after preview: "
            + "; ".join(exc.messages),
        )
    else:
        messages.success(request, f"Imported {len(created)} {kind} row(s).")
    return HttpResponseRedirect(reverse("admin_metadata_transfer"))
