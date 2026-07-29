from rest_framework import serializers


class AnalyticsDateRangeSerializer(serializers.Serializer):
    dateFrom = serializers.DateField(required=False)
    dateTo = serializers.DateField(required=False)
    limit = serializers.IntegerField(required=False, min_value=1, max_value=50)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if attrs.get("dateFrom") and attrs.get("dateTo"):
            if attrs["dateFrom"] > attrs["dateTo"]:
                raise serializers.ValidationError(
                    {"dateTo": "Must be on or after dateFrom."}
                )
            if (attrs["dateTo"] - attrs["dateFrom"]).days > 366:
                raise serializers.ValidationError(
                    {"dateTo": "Date range cannot exceed 366 days."}
                )
        return attrs


class MetricTotalsSerializer(serializers.Serializer):
    totalPlays = serializers.IntegerField()
    uniqueListeners = serializers.IntegerField()
    listeningHours = serializers.DecimalField(max_digits=18, decimal_places=2)
    completionRate = serializers.DecimalField(max_digits=5, decimal_places=2)


class DailyMetricSerializer(MetricTotalsSerializer):
    date = serializers.DateField()


class PopularMetricSerializer(MetricTotalsSerializer):
    id = serializers.UUIDField()
    slug = serializers.CharField()
    name = serializers.CharField()
