from django.urls import path

from apps.accounts.views import (
    ChangePasswordView,
    CurrentUserView,
    GoogleLoginView,
    LoginView,
    LogoutView,
    PreferencesUpdateView,
    ProfileUpdateView,
    RefreshView,
    RegistrationView,
)

app_name = "accounts"

urlpatterns = [
    path("register/", RegistrationView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("google/", GoogleLoginView.as_view(), name="google"),
    path("token/", LoginView.as_view(), name="token"),
    path("token/refresh/", RefreshView.as_view(), name="token-refresh"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("me/", CurrentUserView.as_view(), name="me"),
    path("profile/", ProfileUpdateView.as_view(), name="profile"),
    path("preferences/", PreferencesUpdateView.as_view(), name="preferences"),
    path("change-password/", ChangePasswordView.as_view(), name="change-password"),
]
