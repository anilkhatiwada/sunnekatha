from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from apps.accounts.models import User
from apps.common.audit import administrative_audit_service
from apps.common.models import AdministrativeAuditAction


class AccountStatusService:
    """Apply privileged account-state transitions at one audited trust boundary."""

    @transaction.atomic
    def set_active(self, *, actor: User, user: User, is_active: bool) -> User:
        if not actor.has_perm("accounts.change_user"):
            raise PermissionDenied("You cannot change user account status.")

        target = User.objects.select_for_update().get(pk=user.pk)
        if target.pk == actor.pk and not is_active:
            raise ValidationError("You cannot suspend your own account.")
        if target.is_superuser and not actor.is_superuser:
            raise PermissionDenied("Only a superuser can modify another superuser.")

        if target.is_active != is_active:
            before = {"is_active": target.is_active}
            target.is_active = is_active
            target.save(update_fields=("is_active", "updated_at"))
            administrative_audit_service.record(
                actor=actor,
                action=(
                    AdministrativeAuditAction.USER_REACTIVATED
                    if is_active
                    else AdministrativeAuditAction.USER_SUSPENDED
                ),
                obj=target,
                reason=(
                    "Account reactivated by staff."
                    if is_active
                    else "Account suspended by staff."
                ),
                before=before,
                after={"is_active": target.is_active},
            )
        return target

    def suspend(self, *, actor: User, user: User) -> User:
        return self.set_active(actor=actor, user=user, is_active=False)

    def reactivate(self, *, actor: User, user: User) -> User:
        return self.set_active(actor=actor, user=user, is_active=True)


account_status_service = AccountStatusService()
