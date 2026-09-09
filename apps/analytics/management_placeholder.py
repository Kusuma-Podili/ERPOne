"""Placeholder-free command helpers kept importable without an external task framework."""
from django.utils import timezone
from .models import AnalyticsAlert
from .services import MetricService

def evaluate_alerts():
    triggered=[]
    for alert in AnalyticsAlert.objects.filter(is_active=True).select_related('kpi','kpi__metric'):
        latest=alert.kpi.metric.snapshots.order_by('-captured_for').first()
        if not latest: continue
        value=latest.value; threshold=alert.threshold
        match={'lt':value<threshold,'lte':value<=threshold,'gt':value>threshold,'gte':value>=threshold,'eq':value==threshold}.get(alert.operator,False)
        if match:
            alert.last_triggered_at=timezone.now(); alert.save(update_fields=['last_triggered_at']); triggered.append(alert)
    return triggered
