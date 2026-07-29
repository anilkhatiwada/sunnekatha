import re
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from apps.common.models import AdministrativeAudit
from apps.common.request_context import current_request_identifier

SAFE_FIELDS = {
    "id",
    "slug",
    "identifier",
    "title",
    "title_ne",
    "title_en",
    "name",
    "name_ne",
    "name_en",
    "display_name",
    "email",
    "status",
    "review_status",
    "processing_status",
    "copyright_status",
    "visibility",
    "playlist_type",
    "section_type",
    "is_active",
    "is_staff",
    "is_creator",
    "is_published",
    "is_featured",
    "is_verified",
    "published_at",
    "scheduled_for",
    "starts_at",
    "ends_at",
    "position",
    "sort_order",
}

SENSITIVE_TERMS = {
    "password",
    "token",
    "secret",
    "signature",
    "signed",
    "url",
    "file",
    "audio",
    "transcript",
    "waveform",
    "provider_data",
    "object_key",
}


def redact_text(value):
    text = str(value or "")
    text = re.sub(r"https?://\S+", "[REDACTED_URL]", text, flags=re.IGNORECASE)
    text = re.sub(
        r"(?i)\b(password|token|secret|signature)\s*[:=]\s*\S+",
        r"\1=[REDACTED]",
        text,
    )
    text = re.sub(r"(?i)\bBearer\s+\S+", "Bearer [REDACTED]", text)
    text = re.sub(
        r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b",
        "[REDACTED_TOKEN]",
        text,
    )
    return text


def _safe_value(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, (UUID, Decimal)):
        return str(value)
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def safe_summary(values):
    if not values:
        return {}
    summary = {}
    for key, value in values.items():
        normalized = key.removesuffix("_id")
        if normalized not in SAFE_FIELDS or any(
            term in key.lower() for term in SENSITIVE_TERMS
        ):
            continue
        summary[key] = _safe_value(value)
    return summary


def object_summary(obj, *, fields=None):
    names = fields or SAFE_FIELDS
    values = {}
    for name in names:
        if hasattr(obj, name):
            values[name] = getattr(obj, name)
    return safe_summary(values)


class AdministrativeAuditService:
    def record(
        self,
        *,
        actor,
        action,
        obj,
        reason="",
        before=None,
        after=None,
        request_identifier=None,
    ):
        if not (
            actor
            and actor.is_authenticated
            and actor.is_active
            and actor.is_staff
            and obj is not None
            and getattr(obj, "pk", None) is not None
        ):
            return None
        return AdministrativeAudit.objects.create(
            staff_user=actor,
            action=action,
            object_type=f"{obj._meta.app_label}.{obj._meta.model_name}",
            object_id=str(obj.pk),
            object_repr=str(obj)[:250],
            reason=redact_text(reason)[:2000],
            before_summary=safe_summary(before),
            after_summary=(
                safe_summary(after) if after is not None else object_summary(obj)
            ),
            request_identifier=(
                request_identifier
                if request_identifier is not None
                else current_request_identifier()
            )[:100],
        )

    def record_bulk(
        self,
        *,
        actor,
        action,
        object_type,
        object_count,
        reason="",
        request_identifier=None,
    ):
        if not (
            actor and actor.is_authenticated and actor.is_active and actor.is_staff
        ):
            return None
        return AdministrativeAudit.objects.create(
            staff_user=actor,
            action=action,
            object_type=object_type[:120],
            object_id="bulk",
            object_repr=f"{object_type} ({object_count} rows)"[:250],
            reason=redact_text(reason)[:2000],
            before_summary={},
            after_summary={"count": str(object_count)},
            request_identifier=(
                request_identifier
                if request_identifier is not None
                else current_request_identifier()
            )[:100],
        )


administrative_audit_service = AdministrativeAuditService()
