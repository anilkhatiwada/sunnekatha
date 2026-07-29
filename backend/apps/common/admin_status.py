"""Shared processing-state presentation for operational admin surfaces."""

from django.utils.html import format_html


class ProcessingState:
    DRAFT = "draft"
    UPLOADED = "uploaded"
    QUEUED = "queued"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"
    PUBLISHED = "published"

    CHOICES = (
        (DRAFT, "Draft"),
        (UPLOADED, "Uploaded"),
        (QUEUED, "Queued"),
        (PROCESSING, "Processing"),
        (READY, "Ready"),
        (FAILED, "Failed"),
        (PUBLISHED, "Published"),
    )


PROCESSING_STATE_META = {
    ProcessingState.DRAFT: ("Draft", "edit_note", "info"),
    ProcessingState.UPLOADED: ("Uploaded", "cloud_done", "info"),
    ProcessingState.QUEUED: ("Queued", "schedule", "warning"),
    ProcessingState.PROCESSING: ("Processing", "sync", "info"),
    ProcessingState.READY: ("Ready", "check_circle", "success"),
    ProcessingState.FAILED: ("Failed", "error", "danger"),
    ProcessingState.PUBLISHED: ("Published", "public", "success"),
}


def processing_state_badge(state):
    label, icon, variant = PROCESSING_STATE_META.get(
        state,
        (str(state).replace("_", " ").title(), "help", "info"),
    )
    return format_html(
        '<span class="sk-processing-badge sk-processing-badge--{}">'
        '<span class="material-symbols-outlined" aria-hidden="true">{}</span>'
        "{}</span>",
        variant,
        icon,
        label,
    )


def track_processing_state(track):
    if track.is_published:
        return ProcessingState.PUBLISHED
    job = getattr(track, "processing_job", None)
    if job is not None:
        return job.admin_processing_state
    if track.processing_status == "failed":
        return ProcessingState.FAILED
    if track.processing_status == "processing":
        return ProcessingState.PROCESSING
    if track.processing_status == "ready":
        return ProcessingState.READY
    if track.audio_master_file:
        return ProcessingState.UPLOADED
    return ProcessingState.DRAFT


def upload_processing_state(upload):
    jobs = list(getattr(upload, "_prefetched_processing_jobs", ()))
    if jobs:
        return jobs[0].admin_processing_state
    if upload.status == "confirmed":
        return ProcessingState.UPLOADED
    if upload.status in {"canceled", "expired", "abandoned"}:
        return ProcessingState.FAILED
    return ProcessingState.DRAFT


class ProcessingStatusMediaMixin:
    class Media:
        css = {"all": ("admin/css/processing-status.css",)}
