"""Serializer mixins for controlled field sets and immutable attributes."""

from rest_framework import serializers


class SelectableFieldsSerializerMixin:
    """Allow trusted callers to request a subset via ``fields=``."""

    def __init__(self, *args, **kwargs):
        selected_fields = kwargs.pop("fields", None)
        super().__init__(*args, **kwargs)

        if selected_fields is None:
            return

        allowed = set(selected_fields)
        for field_name in set(self.fields) - allowed:
            self.fields.pop(field_name)


class ImmutableFieldsSerializerMixin:
    """Reject updates to serializer fields declared immutable by a subclass."""

    immutable_fields: tuple[str, ...] = ()

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if not self.instance:
            return attrs

        changed_fields = {
            field
            for field in self.immutable_fields
            if field in attrs and attrs[field] != getattr(self.instance, field, None)
        }
        if changed_fields:
            raise serializers.ValidationError(
                {
                    field: ["This field cannot be changed after creation."]
                    for field in sorted(changed_fields)
                }
            )
        return attrs


class RejectUnknownFieldsMixin:
    """Reject undeclared input instead of silently ignoring mass-assignment attempts."""

    def to_internal_value(self, data):
        if hasattr(data, "keys"):
            unknown = set(data.keys()) - set(self.fields)
            if unknown:
                raise serializers.ValidationError(
                    {
                        field: ["Unknown or non-writable field."]
                        for field in sorted(unknown)
                    }
                )
        return super().to_internal_value(data)
