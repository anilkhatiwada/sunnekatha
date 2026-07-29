from rest_framework import serializers


class ExploreResponseSerializer(serializers.Serializer):
    sections = serializers.ListField(child=serializers.JSONField())
