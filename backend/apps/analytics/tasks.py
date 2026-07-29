from datetime import date, timedelta

from celery import shared_task
from django.db import DatabaseError
from django.utils import timezone

from apps.analytics.services import daily_analytics_aggregation_service


@shared_task(
    autoretry_for=(DatabaseError,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=3,
)
def aggregate_daily_analytics(metric_date=None):
    target = (
        date.fromisoformat(metric_date)
        if metric_date
        else timezone.localdate() - timedelta(days=1)
    )
    metric = daily_analytics_aggregation_service.aggregate(target)
    return {"date": target.isoformat(), "totalPlays": metric.total_plays}
