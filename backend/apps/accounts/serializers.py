from django.contrib.auth import get_user_model, password_validation
from rest_framework import serializers
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from apps.common.serializers import RejectUnknownFieldsMixin

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    displayName = serializers.CharField(source="display_name")
    preferredLanguage = serializers.CharField(source="preferred_language")
    defaultPlaybackSpeed = serializers.FloatField(source="default_playback_speed")
    autoplayEnabled = serializers.BooleanField(source="autoplay_enabled")
    explicitContentEnabled = serializers.BooleanField(source="explicit_content_enabled")
    isCreator = serializers.BooleanField(source="is_creator", read_only=True)
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    updatedAt = serializers.DateTimeField(source="updated_at", read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "username",
            "displayName",
            "avatar",
            "preferredLanguage",
            "defaultPlaybackSpeed",
            "autoplayEnabled",
            "explicitContentEnabled",
            "isCreator",
            "createdAt",
            "updatedAt",
        )
        read_only_fields = fields


class TokenPairWithUserSerializer(serializers.Serializer):
    access = serializers.CharField(read_only=True)
    refresh = serializers.CharField(read_only=True)
    user = UserSerializer(read_only=True)


class RegistrationSerializer(RejectUnknownFieldsMixin, serializers.ModelSerializer):
    displayName = serializers.CharField(source="display_name", min_length=2)
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    passwordConfirm = serializers.CharField(write_only=True, trim_whitespace=False)

    class Meta:
        model = User
        fields = ("email", "username", "displayName", "password", "passwordConfirm")

    def validate_email(self, value):
        email = User.objects.normalize_email(value).lower()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError("An account with this email exists.")
        return email

    def validate(self, attrs):
        attrs = super().validate(attrs)
        password = attrs.get("password")
        if password != attrs.pop("passwordConfirm", None):
            raise serializers.ValidationError(
                {"passwordConfirm": ["Passwords do not match."]}
            )
        password_validation.validate_password(password)
        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password")
        return User.objects.create_user(password=password, **validated_data)


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        attrs[self.username_field] = attrs[self.username_field].strip().lower()
        data = super().validate(attrs)
        data["user"] = UserSerializer(self.user, context=self.context).data
        return data


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField(write_only=True)

    def validate_refresh(self, value):
        try:
            self.token = RefreshToken(value)
        except TokenError as exc:
            raise serializers.ValidationError("Invalid refresh token.") from exc
        if str(self.token["user_id"]) != str(self.context["request"].user.pk):
            raise serializers.ValidationError("Refresh token does not belong to user.")
        return value

    def save(self, **kwargs):
        del kwargs
        self.token.blacklist()


class ProfileUpdateSerializer(RejectUnknownFieldsMixin, serializers.ModelSerializer):
    displayName = serializers.CharField(
        source="display_name",
        min_length=2,
        max_length=100,
        required=False,
    )

    class Meta:
        model = User
        fields = ("email", "username", "displayName", "avatar")
        extra_kwargs = {
            "email": {"required": False},
            "username": {"required": False},
            "avatar": {"required": False},
        }

    def validate_email(self, value):
        email = User.objects.normalize_email(value).lower()
        duplicate = User.objects.filter(email__iexact=email).exclude(
            pk=self.instance.pk
        )
        if duplicate.exists():
            raise serializers.ValidationError("An account with this email exists.")
        return email


class PreferencesUpdateSerializer(
    RejectUnknownFieldsMixin, serializers.ModelSerializer
):
    preferredLanguage = serializers.ChoiceField(
        source="preferred_language",
        choices=User._meta.get_field("preferred_language").choices,
        required=False,
    )
    defaultPlaybackSpeed = serializers.FloatField(
        source="default_playback_speed",
        min_value=0.5,
        max_value=2.0,
        required=False,
    )
    autoplayEnabled = serializers.BooleanField(
        source="autoplay_enabled",
        required=False,
    )
    explicitContentEnabled = serializers.BooleanField(
        source="explicit_content_enabled",
        required=False,
    )

    class Meta:
        model = User
        fields = (
            "preferredLanguage",
            "defaultPlaybackSpeed",
            "autoplayEnabled",
            "explicitContentEnabled",
        )


class ChangePasswordSerializer(serializers.Serializer):
    currentPassword = serializers.CharField(write_only=True, trim_whitespace=False)
    newPassword = serializers.CharField(write_only=True, trim_whitespace=False)
    newPasswordConfirm = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_currentPassword(self, value):
        if not self.context["request"].user.check_password(value):
            raise serializers.ValidationError("The current password is incorrect.")
        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if attrs["newPassword"] != attrs["newPasswordConfirm"]:
            raise serializers.ValidationError(
                {"newPasswordConfirm": ["Passwords do not match."]}
            )
        password_validation.validate_password(
            attrs["newPassword"],
            user=self.context["request"].user,
        )
        return attrs
