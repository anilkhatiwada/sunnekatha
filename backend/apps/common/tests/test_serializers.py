from types import SimpleNamespace

from rest_framework import serializers

from apps.common.serializers import (
    ImmutableFieldsSerializerMixin,
    SelectableFieldsSerializerMixin,
)


class ExampleSerializer(
    SelectableFieldsSerializerMixin,
    ImmutableFieldsSerializerMixin,
    serializers.Serializer,
):
    immutable_fields = ("slug",)

    slug = serializers.CharField()
    title = serializers.CharField()

    def update(self, instance, validated_data):
        return instance

    def create(self, validated_data):
        return SimpleNamespace(**validated_data)


def test_selectable_fields_mixin_limits_serializer_fields():
    serializer = ExampleSerializer(fields=("title",))

    assert set(serializer.fields) == {"title"}


def test_immutable_fields_mixin_rejects_changed_value():
    serializer = ExampleSerializer(
        instance=SimpleNamespace(slug="original", title="Old"),
        data={"slug": "changed", "title": "New"},
    )

    assert serializer.is_valid() is False
    assert "slug" in serializer.errors


def test_immutable_fields_mixin_allows_unchanged_value():
    serializer = ExampleSerializer(
        instance=SimpleNamespace(slug="original", title="Old"),
        data={"slug": "original", "title": "New"},
    )

    assert serializer.is_valid() is True
