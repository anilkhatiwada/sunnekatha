from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.generics import GenericAPIView, RetrieveAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.accounts.google_auth import resolve_google_user, verify_google_credential
from apps.accounts.permissions import IsAuthenticatedAndActive
from apps.accounts.serializers import (
    ChangePasswordSerializer,
    EmailTokenObtainPairSerializer,
    GoogleLoginSerializer,
    LogoutSerializer,
    PreferencesUpdateSerializer,
    ProfileUpdateSerializer,
    RegistrationSerializer,
    TokenPairWithUserSerializer,
    UserSerializer,
)
from apps.common.schema import with_standard_errors


class RegistrationView(GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = RegistrationSerializer
    throttle_scope = "registration"

    @extend_schema(
        summary="Register with email and password",
        description=(
            "Creates an account and returns an access/refresh token pair. Use the "
            "access token as a Bearer token; store the refresh token securely."
        ),
        responses=with_standard_errors({201: TokenPairWithUserSerializer}),
        examples=[
            OpenApiExample(
                "Register",
                value={
                    "email": "srota@example.com",
                    "username": "srota",
                    "displayName": "श्रोता",
                    "password": "StrongPass!234",
                    "passwordConfirm": "StrongPass!234",
                },
                request_only=True,
            ),
            OpenApiExample(
                "Authenticated registration",
                value={
                    "access": "eyJ...access",
                    "refresh": "eyJ...refresh",
                    "user": {
                        "id": "3f743a2f-ce10-4f7e-808f-66a1ba85ba43",
                        "email": "srota@example.com",
                        "username": "srota",
                        "displayName": "श्रोता",
                        "preferredLanguage": "ne",
                        "defaultPlaybackSpeed": 1.0,
                        "autoplayEnabled": False,
                        "explicitContentEnabled": False,
                        "isCreator": False,
                    },
                },
                response_only=True,
                status_codes=["201"],
            ),
        ],
        tags=["auth"],
    )
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token = EmailTokenObtainPairSerializer.get_token(user)
        return Response(
            {
                "access": str(token.access_token),
                "refresh": str(token),
                "user": UserSerializer(user, context={"request": request}).data,
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(TokenObtainPairView):
    permission_classes = [AllowAny]
    serializer_class = EmailTokenObtainPairSerializer
    throttle_scope = "login"


class GoogleLoginView(GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = GoogleLoginSerializer
    throttle_scope = "login"

    def post(self, request):
        if request.headers.get("X-SunneKatha-Auth") != "google":
            raise AuthenticationFailed("Invalid Google login request.")
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = resolve_google_user(
            verify_google_credential(serializer.validated_data["credential"])
        )
        token = EmailTokenObtainPairSerializer.get_token(user)
        return Response(
            {
                "access": str(token.access_token),
                "refresh": str(token),
                "user": UserSerializer(user, context={"request": request}).data,
            }
        )


class RefreshView(TokenRefreshView):
    permission_classes = [AllowAny]
    throttle_scope = "token_refresh"


class LogoutView(GenericAPIView):
    permission_classes = [IsAuthenticatedAndActive]
    serializer_class = LogoutSerializer

    @extend_schema(responses=with_standard_errors({204: None}))
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CurrentUserView(RetrieveAPIView):
    permission_classes = [IsAuthenticatedAndActive]
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


class AccountUpdateView(GenericAPIView):
    permission_classes = [IsAuthenticatedAndActive]
    output_serializer_class = UserSerializer

    def update(self, request, serializer_class):
        serializer = serializer_class(
            request.user,
            data=request.data,
            partial=True,
            context=self.get_serializer_context(),
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            self.output_serializer_class(
                user,
                context=self.get_serializer_context(),
            ).data
        )


class ProfileUpdateView(AccountUpdateView):
    serializer_class = ProfileUpdateSerializer

    def patch(self, request):
        return self.update(request, self.serializer_class)


class PreferencesUpdateView(AccountUpdateView):
    serializer_class = PreferencesUpdateSerializer

    def patch(self, request):
        return self.update(request, self.serializer_class)


class ChangePasswordView(GenericAPIView):
    permission_classes = [IsAuthenticatedAndActive]
    serializer_class = ChangePasswordSerializer
    throttle_scope = "password_change"

    @extend_schema(responses=with_standard_errors({204: None}))
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        user.set_password(serializer.validated_data["newPassword"])
        user.save(update_fields=["password", "updated_at"])

        for token in OutstandingToken.objects.filter(user=user):
            BlacklistedToken.objects.get_or_create(token=token)

        return Response(status=status.HTTP_204_NO_CONTENT)
