from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import transaction
from google.auth.exceptions import GoogleAuthError
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from rest_framework.exceptions import AuthenticationFailed, ValidationError

from apps.accounts.models import SocialIdentity, User


def verify_google_credential(credential):
    if not settings.GOOGLE_OAUTH_CLIENT_ID:
        raise ImproperlyConfigured("Google authentication is not configured.")
    try:
        payload = id_token.verify_oauth2_token(
            credential,
            google_requests.Request(),
            settings.GOOGLE_OAUTH_CLIENT_ID,
        )
    except (ValueError, GoogleAuthError):
        raise AuthenticationFailed("Invalid Google credential.") from None
    if not payload.get("email_verified"):
        raise AuthenticationFailed("Google email is not verified.")
    if not payload.get("sub") or not payload.get("email"):
        raise AuthenticationFailed("Google credential is missing identity claims.")
    return payload


@transaction.atomic
def resolve_google_user(payload):
    subject = str(payload["sub"])
    email = User.objects.normalize_email(payload["email"]).lower()
    identity = (
        SocialIdentity.objects.select_related("user")
        .filter(provider=SocialIdentity.Provider.GOOGLE, subject=subject)
        .first()
    )
    if identity:
        if not identity.user.is_active:
            raise AuthenticationFailed("This account is inactive.")
        return identity.user

    user = User.objects.filter(email__iexact=email).first()
    if user:
        is_authoritative = email.endswith("@gmail.com") or bool(payload.get("hd"))
        if not is_authoritative:
            raise ValidationError(
                {"email": "Sign in with your password before linking Google."}
            )
    else:
        base = email.split("@", 1)[0][:120] or "google-user"
        username = base
        suffix = 1
        while User.objects.filter(username=username).exists():
            suffix += 1
            username = f"{base[:110]}-{suffix}"
        user = User.objects.create_user(
            email=email,
            username=username,
            display_name=(payload.get("name") or base)[:100],
        )
        user.set_unusable_password()
        user.save(update_fields=("password",))

    if not user.is_active:
        raise AuthenticationFailed("This account is inactive.")
    SocialIdentity.objects.create(
        user=user,
        provider=SocialIdentity.Provider.GOOGLE,
        subject=subject,
        email_at_link=email,
    )
    return user
