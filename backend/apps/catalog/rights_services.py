from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from apps.catalog.models import (
    PermissionDocument,
    PermissionDocumentAudit,
    PermissionDocumentAuditAction,
)
from apps.common.audit import administrative_audit_service
from apps.common.models import AdministrativeAuditAction


class PermissionDocumentService:
    @staticmethod
    def _require_change_permission(actor):
        if not (
            actor
            and actor.is_authenticated
            and actor.is_active
            and actor.is_staff
            and actor.has_perm("catalog.verify_permissiondocument")
        ):
            raise PermissionDenied(
                "Rights document verification permission is required."
            )

    @transaction.atomic
    def verify(self, *, queryset, actor) -> int:
        self._require_change_permission(actor)
        documents = list(
            PermissionDocument.objects.select_for_update()
            .filter(pk__in=queryset, is_verified=False)
            .exclude(document="")
        )
        now = timezone.now()
        for document in documents:
            document.is_verified = True
            document.verified_by = actor
            document.verified_at = now
            document.save(
                update_fields=(
                    "is_verified",
                    "verified_by",
                    "verified_at",
                    "updated_at",
                )
            )
            PermissionDocumentAudit.objects.create(
                document=document,
                actor=actor,
                action=PermissionDocumentAuditAction.VERIFIED,
            )
            administrative_audit_service.record(
                actor=actor,
                action=AdministrativeAuditAction.COPYRIGHT_VERIFIED,
                obj=document,
                reason="Permission document verified.",
                before={"is_verified": False},
                after={"is_verified": True},
            )
        return len(documents)

    @transaction.atomic
    def revoke_verification(self, *, queryset, actor) -> int:
        self._require_change_permission(actor)
        documents = list(
            PermissionDocument.objects.select_for_update().filter(
                pk__in=queryset,
                is_verified=True,
            )
        )
        for document in documents:
            previous_verifier = document.verified_by_id
            previous_date = document.verified_at
            document.is_verified = False
            document.verified_by = None
            document.verified_at = None
            document.save(
                update_fields=(
                    "is_verified",
                    "verified_by",
                    "verified_at",
                    "updated_at",
                )
            )
            PermissionDocumentAudit.objects.create(
                document=document,
                actor=actor,
                action=PermissionDocumentAuditAction.VERIFICATION_REVOKED,
                details={
                    "previousVerifierId": (
                        str(previous_verifier) if previous_verifier else None
                    ),
                    "previousVerificationDate": (
                        previous_date.isoformat() if previous_date else None
                    ),
                },
            )
            administrative_audit_service.record(
                actor=actor,
                action=AdministrativeAuditAction.COPYRIGHT_REVOKED,
                obj=document,
                reason="Permission document verification revoked.",
                before={"is_verified": True},
                after={"is_verified": False},
            )
        return len(documents)

    def record_download(self, *, document, actor, preview=False):
        if not (
            actor.has_perm("catalog.view_permissiondocument")
            or actor.has_perm("catalog.change_permissiondocument")
        ):
            raise PermissionDenied("Rights document view permission is required.")
        if not document.document:
            raise ValidationError("No stored document is available.")
        PermissionDocumentAudit.objects.create(
            document=document,
            actor=actor,
            action=PermissionDocumentAuditAction.DOWNLOADED,
            details={"preview": bool(preview)},
        )


permission_document_service = PermissionDocumentService()
